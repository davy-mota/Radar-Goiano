from fastapi import APIRouter, Query
from sqlalchemy import text

from database import engine
from .sql_utils import por_mes, serie_mensal_combinada


router = APIRouter(prefix="/api/fiscal", tags=["orçamento e receita"])
LIMIAR_COBERTURA_PREVISAO = 70.0


def avaliar_previsao(previsto, total_registros: int, registros_com_previsao: int) -> dict:
    cobertura = (registros_com_previsao / total_registros * 100) if total_registros else 0.0
    return {
        "valor": previsto,
        "cobertura_percentual": cobertura,
        "confiavel_para_percentual": cobertura >= LIMIAR_COBERTURA_PREVISAO,
        "limiar_percentual": LIMIAR_COBERTURA_PREVISAO,
    }


def _somar(conexao, tabela: str, coluna_valor: str, where: str, parametros: dict):
    return conexao.execute(
        text(f"SELECT COALESCE(SUM({coluna_valor}), 0) FROM {tabela} {where}"), parametros
    ).scalar_one()


@router.get("/resumo")
def resumo_fiscal(
    ano: int = Query(default=2025, ge=2006, le=2100),
    mes: int | None = Query(default=None, ge=1, le=12),
):
    filtro_mes_receita = " AND mes = :mes" if mes is not None else ""
    filtro_mes_despesa = " AND mes = :mes" if mes is not None else ""
    parametros = {"ano": ano, "mes": mes}
    where_despesa = f"WHERE ano_exercicio = :ano{filtro_mes_despesa}"

    with engine.connect() as conexao:
        receita = dict(conexao.execute(text(f"""
            SELECT COUNT(*) AS registros,
                   COUNT(*) FILTER (WHERE valor_previsto > 0) AS registros_com_previsao,
                   COALESCE(SUM(valor_previsto), 0) AS previsto,
                   COALESCE(SUM(valor_realizado), 0) AS arrecadado
            FROM vw_receitas_ativas
            WHERE ano = :ano {filtro_mes_receita}
        """), parametros).mappings().one())

        despesa_registros = conexao.execute(
            text(f"SELECT COUNT(*) FROM vw_pagamentos_ativos {where_despesa}"), parametros
        ).scalar_one()
        despesa = {
            "registros": despesa_registros,
            "empenhado": _somar(conexao, "vw_empenhos_ativos", "valor_empenhado", where_despesa, parametros),
            "liquidado": _somar(conexao, "vw_liquidacoes_ativas", "valor_liquidado", where_despesa, parametros),
            "pago": _somar(conexao, "vw_pagamentos_ativos", "valor_pago", where_despesa, parametros),
        }

        receitas_mensais = por_mes(conexao.execute(text("""
            SELECT mes, COALESCE(SUM(valor_previsto), 0) AS previsto,
                   COALESCE(SUM(valor_realizado), 0) AS arrecadado
            FROM vw_receitas_ativas
            WHERE ano = :ano
            GROUP BY mes
        """), {"ano": ano}).mappings().all())
        empenhos_mensais = por_mes(conexao.execute(text("""
            SELECT mes, COALESCE(SUM(valor_empenhado), 0) AS empenhado
            FROM vw_empenhos_ativos WHERE ano_exercicio = :ano GROUP BY mes
        """), {"ano": ano}).mappings().all())
        liquidacoes_mensais = por_mes(conexao.execute(text("""
            SELECT mes, COALESCE(SUM(valor_liquidado), 0) AS liquidado
            FROM vw_liquidacoes_ativas WHERE ano_exercicio = :ano GROUP BY mes
        """), {"ano": ano}).mappings().all())
        pagamentos_mensais = por_mes(conexao.execute(text("""
            SELECT mes, COALESCE(SUM(valor_pago), 0) AS pago
            FROM vw_pagamentos_ativos WHERE ano_exercicio = :ano GROUP BY mes
        """), {"ano": ano}).mappings().all())

        categorias = conexao.execute(text(f"""
            SELECT COALESCE(categoria_economica, 'Não informada') AS nome,
                   COALESCE(SUM(valor_realizado), 0) AS valor
            FROM vw_receitas_ativas
            WHERE ano = :ano {filtro_mes_receita}
            GROUP BY categoria_economica
            ORDER BY valor DESC
            LIMIT 8
        """), parametros).mappings().all()

    previsao = avaliar_previsao(
        receita["previsto"], receita["registros"], receita["registros_com_previsao"]
    )
    percentual_arrecadado = None
    if previsao["confiavel_para_percentual"] and receita["previsto"]:
        percentual_arrecadado = float(receita["arrecadado"] / receita["previsto"] * 100)

    serie_mensal = serie_mensal_combinada(receitas_mensais, empenhos_mensais, liquidacoes_mensais, pagamentos_mensais)

    return {
        "ano": ano,
        "mes": mes,
        "receita": {
            "registros": receita["registros"],
            "previsto": previsao,
            "arrecadado": receita["arrecadado"],
            "percentual_arrecadado_da_previsao": percentual_arrecadado,
        },
        "despesa": despesa,
        "saldo_financeiro_observado": receita["arrecadado"] - despesa["pago"],
        "serie_mensal": serie_mensal,
        "top_categorias_receita": [dict(item) for item in categorias],
        "metodologia": (
            "Saldo financeiro observado = receita arrecadada - despesa paga nos registros disponíveis. "
            "Não equivale ao resultado orçamentário oficial. Empenho não equivale à dotação."
        ),
    }


@router.get("/anos")
def anos_fiscais():
    with engine.connect() as conexao:
        anos = conexao.execute(text("""
            SELECT ano FROM (
                SELECT DISTINCT ano AS ano FROM vw_receitas_ativas
                INTERSECT
                SELECT DISTINCT ano_exercicio AS ano FROM vw_pagamentos_ativos
            ) AS cobertura
            WHERE ano IS NOT NULL
            ORDER BY ano DESC
        """)).scalars().all()
    return {"anos": anos}
