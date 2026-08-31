import argparse
import json
import sys

from sqlalchemy import text

from carga_financeira_versionada import CATALOGOS, catalogo
from database import engine


def _normalizar_timestamp(valor) -> str | None:
    if not valor:
        return None
    texto = valor.isoformat() if hasattr(valor, "isoformat") else str(valor)
    return texto[:19]


def verificar_estabilidade_fonte(versao_id: int) -> dict:
    """Confere se os recursos baixados para a versão continuam publicados e
    com a mesma data de modificação no catálogo oficial. Um recurso removido
    é tratado como divergência bloqueante; uma data de modificação diferente
    é registrada como aviso, pois recursos do ano corrente são atualizados
    legitimamente pela fonte após o download."""
    with engine.connect() as conexao:
        recursos = conexao.execute(text("""
            SELECT conjunto, recurso_ckan_id, nome, modificado_em
            FROM recursos_ingestao WHERE versao_id = :versao
        """), {"versao": versao_id}).mappings().all()

    divergencias = []
    avisos = []
    conjuntos = {r["conjunto"] for r in recursos}
    catalogos_atuais = {conjunto: {r["id"]: r for r in catalogo(conjunto)} for conjunto in conjuntos}

    for recurso in recursos:
        atual = catalogos_atuais[recurso["conjunto"]].get(str(recurso["recurso_ckan_id"]))
        if atual is None:
            divergencias.append(f"{recurso['conjunto']}/{recurso['nome']}: recurso não está mais publicado no catálogo oficial")
        elif _normalizar_timestamp(atual.get("last_modified")) != _normalizar_timestamp(recurso["modificado_em"]):
            avisos.append(f"{recurso['conjunto']}/{recurso['nome']}: catálogo indica modificação após o download")

    return {"recursos_verificados": len(recursos), "divergencias": divergencias, "avisos": avisos}


def _iniciar_registro(descricao: str) -> int:
    with engine.begin() as conexao:
        return conexao.execute(text("""
            INSERT INTO historico_cargas (conjunto, status, fonte)
            VALUES ('ativacao_versao', 'em_execucao', :descricao)
            RETURNING id
        """), {"descricao": descricao}).scalar_one()


def _finalizar_registro(carga_id: int, status: str, registros: int | None = None, erro: str | None = None):
    with engine.begin() as conexao:
        conexao.execute(text("""
            UPDATE historico_cargas
            SET status = :status, finalizado_em = NOW(),
                registros_processados = :registros,
                duracao_segundos = EXTRACT(EPOCH FROM (NOW() - iniciado_em)),
                mensagem_erro = :erro
            WHERE id = :id
        """), {"id": carga_id, "status": status, "registros": registros, "erro": erro[:2000] if erro else None})


def _trocar_versao_ativa(versao_id: int, status_exigido: str, metricas_extra: dict, descricao: str) -> int:
    with engine.connect() as conexao:
        versao = conexao.execute(text("SELECT status FROM versoes_dados WHERE id=:id"), {"id": versao_id}).mappings().first()
    if versao is None:
        raise ValueError(f"Versão {versao_id} não encontrada.")
    if versao["status"] != status_exigido:
        raise ValueError(f"Versão {versao_id} está com status '{versao['status']}'; era esperado '{status_exigido}'.")

    carga_id = _iniciar_registro(descricao)
    try:
        with engine.begin() as conexao:
            total = conexao.execute(text("""
                SELECT COALESCE(SUM(registros), 0) FROM recursos_ingestao WHERE versao_id = :versao
            """), {"versao": versao_id}).scalar_one()
            conexao.execute(text("UPDATE versoes_dados SET status='arquivada' WHERE status='ativa'"))
            conexao.execute(text("""
                UPDATE versoes_dados
                SET status='ativa',
                    observacao = COALESCE(observacao, '') || ' | ' || :descricao,
                    metricas = metricas || CAST(:extra AS jsonb)
                WHERE id = :id
            """), {"id": versao_id, "descricao": descricao, "extra": json.dumps(metricas_extra, default=str)})
            conexao.execute(text("SELECT atualizar_metadados_qualidade()"))
        _finalizar_registro(carga_id, "sucesso", registros=int(total))
        return int(total)
    except Exception as erro:
        _finalizar_registro(carga_id, "falha", erro=str(erro))
        raise


def ativar(versao_id: int, ignorar_divergencias: bool = False) -> int:
    estabilidade = verificar_estabilidade_fonte(versao_id)
    if estabilidade["divergencias"] and not ignorar_divergencias:
        raise ValueError(
            "Ativação bloqueada por recursos removidos do catálogo oficial: "
            + "; ".join(estabilidade["divergencias"])
            + ". Use --ignorar-divergencias para prosseguir mesmo assim."
        )
    descricao = f"ativação da versão {versao_id} via ativar_versao.py"
    total = _trocar_versao_ativa(versao_id, "validada", {"estabilidade_fonte": estabilidade}, descricao)
    for aviso in estabilidade["avisos"]:
        print(f"aviso: {aviso}", file=sys.stderr)
    return total


def reverter(versao_id: int) -> int:
    descricao = f"reversão para a versão {versao_id} via ativar_versao.py --reverter"
    return _trocar_versao_ativa(versao_id, "arquivada", {}, descricao)


def listar() -> None:
    with engine.connect() as conexao:
        linhas = conexao.execute(text("""
            SELECT id, status, iniciado_em, finalizado_em, observacao
            FROM versoes_dados ORDER BY id DESC
        """)).mappings().all()
    for linha in linhas:
        print(f"#{linha['id']:<4} {linha['status']:<10} iniciada={linha['iniciado_em']} finalizada={linha['finalizado_em']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Promove, reverte ou lista versões da carga financeira versionada.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--listar", action="store_true", help="Lista as versões existentes e seus status.")
    grupo.add_argument("--ativar", type=int, metavar="ID", help="Ativa a versão ID (precisa estar 'validada').")
    grupo.add_argument("--reverter", type=int, metavar="ID", help="Reativa a versão ID (precisa estar 'arquivada').")
    parser.add_argument("--ignorar-divergencias", action="store_true",
                         help="Prossegue com a ativação mesmo se algum recurso tiver sido removido do catálogo oficial.")
    argumentos = parser.parse_args()

    try:
        if argumentos.listar:
            listar()
        elif argumentos.ativar is not None:
            total = ativar(argumentos.ativar, argumentos.ignorar_divergencias)
            print(f"Versão {argumentos.ativar} ativada com {total:,} registros somados entre os recursos.")
        else:
            total = reverter(argumentos.reverter)
            print(f"Versão {argumentos.reverter} reativada com {total:,} registros somados entre os recursos.")
    except Exception as erro:
        print(f"Falhou: {erro}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
