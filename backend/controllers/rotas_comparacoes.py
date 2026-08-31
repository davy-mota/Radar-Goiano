from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from database import engine
from .sql_utils import ORGAO_NORMALIZADO, por_mes, serie_mensal_combinada


router = APIRouter(prefix="/api/comparacoes", tags=["comparações"])


def validar_cenario(orgao: str, ano: int) -> tuple[str, int]:
    orgao_limpo = orgao.strip()
    if not orgao_limpo or len(orgao_limpo) > 250:
        raise HTTPException(status_code=422, detail="Órgão inválido.")
    if not 2003 <= ano <= 2100:
        raise HTTPException(status_code=422, detail="Ano inválido.")
    return orgao_limpo, ano


def variacao_percentual(valor_a: float, valor_b: float) -> float | None:
    if not valor_a:
        return None
    return ((valor_b - valor_a) / abs(valor_a)) * 100


def _somar(conexao, tabela: str, coluna_valor: str, where: str, parametros: dict):
    return conexao.execute(
        text(f"SELECT COALESCE(SUM({coluna_valor}), 0) FROM {tabela} {where}"), parametros
    ).scalar_one()


def carregar_cenario(conexao, orgao: str, ano: int) -> dict:
    parametros = {"orgao": orgao, "ano": ano}
    where = f"WHERE {ORGAO_NORMALIZADO} = :orgao AND ano_exercicio = :ano"

    registros = conexao.execute(text(f"SELECT COUNT(*) FROM vw_pagamentos_ativos {where}"), parametros).scalar_one()
    credores_distintos = conexao.execute(
        text(f"SELECT COUNT(DISTINCT nome_credor) FROM vw_pagamentos_ativos {where}"), parametros
    ).scalar_one()
    empenhado = _somar(conexao, "vw_empenhos_ativos", "valor_empenhado", where, parametros)
    liquidado = _somar(conexao, "vw_liquidacoes_ativas", "valor_liquidado", where, parametros)
    pago = _somar(conexao, "vw_pagamentos_ativos", "valor_pago", where, parametros)
    kpis = {"registros": registros, "credores": credores_distintos, "empenhado": empenhado, "liquidado": liquidado, "pago": pago}

    serie_empenhos = por_mes(conexao.execute(text(f"""
        SELECT mes, COALESCE(SUM(valor_empenhado), 0) AS empenhado FROM vw_empenhos_ativos {where} GROUP BY mes
    """), parametros).mappings().all())
    serie_liquidacoes = por_mes(conexao.execute(text(f"""
        SELECT mes, COALESCE(SUM(valor_liquidado), 0) AS liquidado FROM vw_liquidacoes_ativas {where} GROUP BY mes
    """), parametros).mappings().all())
    serie_pagamentos = por_mes(conexao.execute(text(f"""
        SELECT mes, COALESCE(SUM(valor_pago), 0) AS pago FROM vw_pagamentos_ativos {where} GROUP BY mes
    """), parametros).mappings().all())

    credores = conexao.execute(text(f"""
        SELECT COALESCE(nome_credor, 'Não informado') AS nome,
               COALESCE(SUM(valor_pago), 0) AS valor
        FROM vw_pagamentos_ativos
        {where}
        GROUP BY nome_credor
        ORDER BY valor DESC
        LIMIT 8
    """), parametros).mappings().all()

    kpis["saldo_liquidado"] = kpis["liquidado"] - kpis["pago"]
    kpis["percentual_pago"] = (
        float(kpis["pago"] / kpis["empenhado"] * 100) if kpis["empenhado"] else None
    )
    total_top_credor = credores[0]["valor"] if credores else 0
    kpis["concentracao_maior_credor"] = (
        float(total_top_credor / kpis["pago"] * 100) if kpis["pago"] else None
    )

    return {
        "orgao": orgao,
        "ano": ano,
        "kpis": kpis,
        "serie_mensal": serie_mensal_combinada(serie_empenhos, serie_liquidacoes, serie_pagamentos),
        "top_credores": [dict(item) for item in credores],
    }


@router.get("/orgaos")
def comparar_orgaos(
    orgao_a: str = Query(min_length=1, max_length=250),
    ano_a: int = Query(ge=2003, le=2100),
    orgao_b: str = Query(min_length=1, max_length=250),
    ano_b: int = Query(ge=2003, le=2100),
):
    orgao_a, ano_a = validar_cenario(orgao_a, ano_a)
    orgao_b, ano_b = validar_cenario(orgao_b, ano_b)

    with engine.connect() as conexao:
        cenario_a = carregar_cenario(conexao, orgao_a, ano_a)
        cenario_b = carregar_cenario(conexao, orgao_b, ano_b)

    comparacao = {
        chave: variacao_percentual(float(cenario_a["kpis"][chave]), float(cenario_b["kpis"][chave]))
        for chave in ("empenhado", "liquidado", "pago", "registros", "credores")
    }
    return {
        "cenario_a": cenario_a,
        "cenario_b": cenario_b,
        "variacao_percentual_b_sobre_a": comparacao,
        "metodologia": (
            "Variação nominal: (cenário B - cenário A) / |cenário A|. "
            "Os valores não estão corrigidos pela inflação."
        ),
    }
