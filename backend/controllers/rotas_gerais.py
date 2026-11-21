from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from database import engine
from .cache_utils import ANOS_VALIDOS, carregar_cache


router = APIRouter(prefix="/api/geral", tags=["visão geral"])
MESES = (
    "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def _fontes_complementares(ano: str) -> list[dict]:
    configuracao = [
        ("Folha de pagamento", "folha", "total_folha", "qtd_servidores"),
        ("Contratos formalizados", "contratos", "valor_total", "qtd_contratos"),
        ("Diárias e passagens", "diarias", "total_gasto", "qtd_viagens"),
    ]
    fontes = []
    for nome, prefixo, campo_valor, campo_registros in configuracao:
        cache = carregar_cache(prefixo, ano)
        kpis = cache.get("kpis", {})
        registros = int(kpis.get(campo_registros) or 0)
        fontes.append({
            "nome": nome,
            "valor": kpis.get(campo_valor) if registros else None,
            "registros": registros,
            "disponivel": registros > 0,
        })
    return fontes


def _texto_cobertura(ano: str, anos: list[int], meses: list[int]) -> str:
    if ano != "todos":
        if not meses:
            return f"Sem pagamentos publicados para {ano}."
        return f"Janeiro a {MESES[meses[-1]]} de {ano}"
    if not anos:
        return "Sem períodos financeiros publicados."
    return f"{anos[0]} a {anos[-1]}"


@router.get("/resumo")
def get_resumo_geral(ano: str = "todos"):
    if ano not in ANOS_VALIDOS:
        raise HTTPException(status_code=422, detail="Ano inválido.")

    parametros = {} if ano == "todos" else {"ano": int(ano)}
    filtro_despesa = "" if ano == "todos" else " WHERE ano_exercicio = :ano"
    filtro_receita = "" if ano == "todos" else " WHERE ano = :ano"

    with engine.connect() as conexao:
        etapas = conexao.execute(text(f"""
            SELECT etapa, COALESCE(SUM(valor), 0) AS valor,
                   COALESCE(SUM(registros), 0) AS registros
            FROM mv_despesas_execucao_mensal
            {filtro_despesa}
            GROUP BY etapa
        """), parametros).mappings().all()
        top_orgaos = conexao.execute(text(f"""
            SELECT nome_orgao AS nome, COALESCE(SUM(valor), 0) AS total
            FROM mv_despesas_execucao_mensal
            {filtro_despesa}
              {"AND" if filtro_despesa else "WHERE"} etapa = 'pago' AND nome_orgao <> ''
            GROUP BY nome_orgao
            ORDER BY total DESC
            LIMIT 5
        """), parametros).mappings().all()
        periodos = conexao.execute(text(f"""
            SELECT DISTINCT ano_exercicio AS ano, mes
            FROM mv_despesas_execucao_mensal
            {filtro_despesa}
              {"AND" if filtro_despesa else "WHERE"} etapa = 'pago'
            ORDER BY ano, mes
        """), parametros).mappings().all()
        receita = conexao.execute(text(f"""
            SELECT COALESCE(SUM(valor_realizado), 0) AS realizado,
                   COUNT(*) AS registros
            FROM vw_receitas_ativas
            {filtro_receita}
        """), parametros).mappings().one()

    totais = {
        linha["etapa"]: {
            "valor": linha["valor"],
            "registros": int(linha["registros"] or 0),
        }
        for linha in etapas
    }
    anos = sorted({int(item["ano"]) for item in periodos if item["ano"] is not None})
    meses = sorted({int(item["mes"]) for item in periodos if item["mes"] is not None})
    cache_legado = carregar_cache("visao_geral", ano)

    return {
        "ano": ano,
        "financeiro": {
            "empenhado": totais.get("empenhado", {"valor": 0, "registros": 0}),
            "liquidado": totais.get("liquidado", {"valor": 0, "registros": 0}),
            "pago": totais.get("pago", {"valor": 0, "registros": 0}),
            "receita_realizada": {
                "valor": receita["realizado"],
                "registros": int(receita["registros"] or 0),
            },
        },
        "cobertura": {
            "anos": anos,
            "meses": meses if ano != "todos" else [],
            "texto": _texto_cobertura(ano, anos, meses),
        },
        "top_orgaos": [dict(item) for item in top_orgaos],
        "fontes_complementares": _fontes_complementares(ano),
        "radar_ia_geral": cache_legado.get("radar_ia_geral", []),
    }
