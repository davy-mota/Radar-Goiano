import argparse
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from database import engine


BASE_DIR = Path(__file__).resolve().parent
EXTRATORES = {
    "pagamentos": {"script": "extracao_de_gastos.py", "tabela": "pagamentos_estaduais", "fonte": "https://dadosabertos.go.gov.br/api/3/action/package_show?id=pagamentos", "habilitado": False},
    "receitas": {"script": "extracao_receitas.py", "tabela": "receitas_estaduais", "fonte": "https://dadosabertos.go.gov.br/api/3/action/package_show?id=receitas-detalhadas", "habilitado": False},
    "contratos": {"script": "extrator_contratos.py", "tabela": "contratos_licitacoes", "fonte": "https://dadosabertos.go.gov.br/api/3/action/package_search?q=contrato"},
    "folha": {"script": "extrator_folha.py", "tabela": "folha_pagamento", "fonte": "https://dadosabertos.go.gov.br/api/3/action/package_search?q=folha"},
    "diarias": {"script": "extrator_diarias.py", "tabela": "diarias_passagens", "fonte": "https://dadosabertos.go.gov.br/api/3/action/package_search?q=diarias"},
}


def validar_conjunto(conjunto: str) -> dict[str, str | bool]:
    try:
        return EXTRATORES[conjunto]
    except KeyError as erro:
        opcoes = ", ".join(EXTRATORES)
        raise ValueError(f"Conjunto inválido. Opções: {opcoes}.") from erro


def iniciar_carga(conjunto: str, fonte: str) -> int:
    with engine.begin() as conexao:
        return conexao.execute(text("""
            INSERT INTO historico_cargas (conjunto, status, fonte)
            VALUES (:conjunto, 'em_execucao', :fonte)
            RETURNING id
        """), {"conjunto": conjunto, "fonte": fonte}).scalar_one()


def contar_registros(tabela: str) -> int:
    # O identificador vem exclusivamente da lista fechada EXTRATORES.
    with engine.connect() as conexao:
        return conexao.execute(text(f'SELECT COUNT(*) FROM "{tabela}"')).scalar_one()


def finalizar_carga(carga_id: int, status: str, registros: int | None = None, erro: str | None = None):
    with engine.begin() as conexao:
        conexao.execute(text("""
            UPDATE historico_cargas
            SET status = :status,
                finalizado_em = NOW(),
                registros_processados = :registros,
                duracao_segundos = EXTRACT(EPOCH FROM (NOW() - iniciado_em)),
                mensagem_erro = :erro
            WHERE id = :id
        """), {"id": carga_id, "status": status, "registros": registros, "erro": erro[:2000] if erro else None})


def executar(conjunto: str) -> int:
    configuracao = validar_conjunto(conjunto)
    if configuracao.get("habilitado") is False:
        print(
            f"Carga de {conjunto} bloqueada: o extrator legado usa append ou não é compatível "
            "com o esquema atual da fonte. Consulte docs/AUDITORIA_QUALIDADE_DADOS.md.",
            file=sys.stderr,
        )
        return 2
    carga_id = iniciar_carga(conjunto, configuracao["fonte"])
    print(f"Carga #{carga_id} iniciada para {conjunto}.")
    try:
        resultado = subprocess.run([sys.executable, str(BASE_DIR / configuracao["script"])], cwd=BASE_DIR, check=False)
        if resultado.returncode != 0:
            mensagem = f"Extrator encerrado com código {resultado.returncode}. Consulte o log do processo."
            finalizar_carga(carga_id, "falha", erro=mensagem)
            print(mensagem, file=sys.stderr)
            return resultado.returncode

        registros = contar_registros(configuracao["tabela"])
        finalizar_carga(carga_id, "sucesso", registros=registros)
        with engine.begin() as conexao:
            conexao.execute(text("SELECT atualizar_metadados_qualidade()"))
        print(f"Carga #{carga_id} concluída com {registros} registros na tabela oficial.")
        return 0
    except Exception as erro:
        finalizar_carga(carga_id, "falha", erro=str(erro))
        print(f"Carga #{carga_id} falhou: {erro}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa e audita uma carga do Radar Goiano.")
    parser.add_argument("conjunto", choices=tuple(EXTRATORES))
    argumentos = parser.parse_args()
    return executar(argumentos.conjunto)


if __name__ == "__main__":
    raise SystemExit(main())
