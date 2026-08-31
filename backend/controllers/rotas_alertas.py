from typing import Literal

from fastapi import APIRouter, Query
from sqlalchemy import text

from database import engine
from .sql_utils import CREDOR_NORMALIZADO, ORGAO_NORMALIZADO


router = APIRouter(prefix="/api/alertas", tags=["alertas explicáveis"])

LIMITE_RESULTADOS = 25
LIMIAR_CONCENTRACAO = 50.0
LIMIAR_TOTAL_ORGAO = 1_000_000
LIMIAR_CREDORES_ORGAO = 5
LIMIAR_CRESCIMENTO_MENSAL = 200.0
LIMIAR_MES_ANTERIOR = 1_000_000
LIMIAR_MES_ATUAL = 5_000_000
MULTIPLICADOR_IQR = 3.0
MINIMO_GRUPO_IQR = 100


def percentual_variacao(anterior, atual) -> float | None:
    if not anterior:
        return None
    return float((atual - anterior) / abs(anterior) * 100)


def _total_e_itens(linhas) -> tuple[int, list[dict]]:
    total = linhas[0]["total_alertas"] if linhas else 0
    itens = []
    for linha in linhas:
        item = dict(linha)
        item.pop("total_alertas", None)
        itens.append(item)
    return total, itens


def _duplicidades(conexao, ano: int) -> dict:
    linhas = conexao.execute(text(f"""
        WITH grupos AS (
            SELECT {ORGAO_NORMALIZADO} AS orgao,
                   COALESCE({CREDOR_NORMALIZADO}, 'Não informado') AS favorecido,
                   numero_empenho, data_pagamento, valor_pago,
                   COUNT(*) AS repeticoes,
                   SUM(valor_pago) AS valor_agregado
            FROM vw_pagamentos_ativos
            WHERE ano_exercicio = :ano AND valor_pago > 0
            GROUP BY {ORGAO_NORMALIZADO}, {CREDOR_NORMALIZADO},
                     numero_empenho, data_pagamento, valor_pago
            HAVING COUNT(*) > 1
        )
        SELECT *, COUNT(*) OVER() AS total_alertas
        FROM grupos
        ORDER BY valor_agregado DESC
        LIMIT :limite
    """), {"ano": ano, "limite": LIMITE_RESULTADOS}).mappings().all()
    total, itens = _total_e_itens(linhas)
    return {
        "tipo": "duplicidade",
        "titulo": "Duplicidades potenciais",
        "total": total,
        "regra": "Mesmos órgão, favorecido, empenho, data e valor pago aparecem mais de uma vez.",
        "ressalva": "Parcelas, retenções ou registros contábeis legítimos podem compartilhar essa assinatura.",
        "itens": itens,
    }


def _concentracoes(conexao, ano: int) -> dict:
    linhas = conexao.execute(text(f"""
        WITH por_credor AS (
            SELECT {ORGAO_NORMALIZADO} AS orgao,
                   COALESCE({CREDOR_NORMALIZADO}, 'Não informado') AS favorecido,
                   SUM(valor_pago) AS valor
            FROM vw_pagamentos_ativos
            WHERE ano_exercicio = :ano AND valor_pago > 0
            GROUP BY {ORGAO_NORMALIZADO}, {CREDOR_NORMALIZADO}
        ), totais AS (
            SELECT orgao, SUM(valor) AS total_orgao, COUNT(*) AS quantidade_credores
            FROM por_credor GROUP BY orgao
        ), alertas AS (
            SELECT p.orgao, p.favorecido, p.valor, t.total_orgao,
                   t.quantidade_credores,
                   (p.valor / NULLIF(t.total_orgao, 0) * 100) AS concentracao_percentual
            FROM por_credor p JOIN totais t USING (orgao)
            WHERE t.total_orgao >= :total_minimo
              AND t.quantidade_credores >= :credores_minimo
              AND (p.valor / NULLIF(t.total_orgao, 0) * 100) >= :concentracao
        )
        SELECT *, COUNT(*) OVER() AS total_alertas
        FROM alertas
        ORDER BY concentracao_percentual DESC, valor DESC
        LIMIT :limite
    """), {
        "ano": ano, "limite": LIMITE_RESULTADOS,
        "total_minimo": LIMIAR_TOTAL_ORGAO,
        "credores_minimo": LIMIAR_CREDORES_ORGAO,
        "concentracao": LIMIAR_CONCENTRACAO,
    }).mappings().all()
    total, itens = _total_e_itens(linhas)
    return {
        "tipo": "concentracao",
        "titulo": "Concentração em favorecido",
        "total": total,
        "regra": (
            f"Um favorecido representa ao menos {LIMIAR_CONCENTRACAO:.0f}% do valor pago por um órgão "
            f"com total acima de R$ {LIMIAR_TOTAL_ORGAO:,.0f} e no mínimo {LIMIAR_CREDORES_ORGAO} favorecidos."
        ),
        "ressalva": "Concentração pode decorrer da natureza da política pública ou de fornecedor exclusivo.",
        "itens": itens,
    }


def _variacoes(conexao, ano: int) -> dict:
    linhas = conexao.execute(text(f"""
        WITH mensal AS (
            SELECT {ORGAO_NORMALIZADO} AS orgao, mes,
                   SUM(valor_pago) AS valor
            FROM vw_pagamentos_ativos
            WHERE ano_exercicio = :ano AND mes BETWEEN 1 AND 12
            GROUP BY {ORGAO_NORMALIZADO}, mes
        ), com_anterior AS (
            SELECT orgao, mes, valor,
                   LAG(valor) OVER (PARTITION BY orgao ORDER BY mes) AS valor_anterior,
                   LAG(mes) OVER (PARTITION BY orgao ORDER BY mes) AS mes_anterior
            FROM mensal
        ), alertas AS (
            SELECT orgao, mes, mes_anterior, valor AS valor_atual, valor_anterior,
                   ((valor - valor_anterior) / NULLIF(ABS(valor_anterior), 0) * 100) AS variacao_percentual
            FROM com_anterior
            WHERE mes_anterior = mes - 1
              AND valor_anterior >= :anterior_minimo
              AND valor >= :atual_minimo
              AND ((valor - valor_anterior) / NULLIF(ABS(valor_anterior), 0) * 100) >= :crescimento
        )
        SELECT *, COUNT(*) OVER() AS total_alertas
        FROM alertas
        ORDER BY variacao_percentual DESC, valor_atual DESC
        LIMIT :limite
    """), {
        "ano": ano, "limite": LIMITE_RESULTADOS,
        "anterior_minimo": LIMIAR_MES_ANTERIOR,
        "atual_minimo": LIMIAR_MES_ATUAL,
        "crescimento": LIMIAR_CRESCIMENTO_MENSAL,
    }).mappings().all()
    total, itens = _total_e_itens(linhas)
    return {
        "tipo": "variacao_mensal",
        "titulo": "Crescimento mensal abrupto",
        "total": total,
        "regra": (
            f"O valor pago cresceu ao menos {LIMIAR_CRESCIMENTO_MENSAL:.0f}% sobre o mês imediatamente anterior, "
            f"partindo de pelo menos R$ {LIMIAR_MES_ANTERIOR:,.0f} e chegando a R$ {LIMIAR_MES_ATUAL:,.0f}."
        ),
        "ressalva": "Sazonalidade, calendário de repasses e fechamento do exercício podem explicar a variação.",
        "itens": itens,
    }


def _atipicos(conexao, ano: int) -> dict:
    linhas = conexao.execute(text(f"""
        WITH base AS (
            SELECT id, {ORGAO_NORMALIZADO} AS orgao,
                   COALESCE({CREDOR_NORMALIZADO}, 'Não informado') AS favorecido,
                   numero_empenho, data_pagamento, valor_pago
            FROM vw_pagamentos_ativos
            WHERE ano_exercicio = :ano AND valor_pago > 0
        ), estatisticas AS (
            SELECT orgao, COUNT(*) AS tamanho_grupo,
                   percentile_cont(0.25) WITHIN GROUP (ORDER BY valor_pago) AS q1,
                   percentile_cont(0.75) WITHIN GROUP (ORDER BY valor_pago) AS q3
            FROM base GROUP BY orgao HAVING COUNT(*) >= :grupo_minimo
        ), alertas AS (
            SELECT b.*, e.tamanho_grupo, e.q1, e.q3,
                   (e.q3 + :multiplicador * (e.q3 - e.q1)) AS limite_superior
            FROM base b JOIN estatisticas e USING (orgao)
            WHERE b.valor_pago > (e.q3 + :multiplicador * (e.q3 - e.q1))
        )
        SELECT *, COUNT(*) OVER() AS total_alertas
        FROM alertas
        ORDER BY valor_pago DESC
        LIMIT :limite
    """), {
        "ano": ano, "limite": LIMITE_RESULTADOS,
        "grupo_minimo": MINIMO_GRUPO_IQR, "multiplicador": MULTIPLICADOR_IQR,
    }).mappings().all()
    total, itens = _total_e_itens(linhas)
    return {
        "tipo": "atipico_iqr",
        "titulo": "Pagamentos atípicos por órgão",
        "total": total,
        "regra": (
            f"Pagamento acima de Q3 + {MULTIPLICADOR_IQR:g} × IQR dentro do mesmo órgão, "
            f"considerando grupos com pelo menos {MINIMO_GRUPO_IQR} registros positivos."
        ),
        "ressalva": "O método identifica distância estatística, não ilegalidade ou erro contábil.",
        "itens": itens,
    }


@router.get("")
def listar_alertas(
    ano: int = Query(default=2025, ge=2003, le=2100),
    tipo: Literal["todos", "duplicidade", "concentracao", "variacao_mensal", "atipico_iqr"] = "todos",
):
    geradores = {
        "duplicidade": _duplicidades,
        "concentracao": _concentracoes,
        "variacao_mensal": _variacoes,
        "atipico_iqr": _atipicos,
    }
    selecionados = geradores.items() if tipo == "todos" else [(tipo, geradores[tipo])]
    with engine.connect() as conexao:
        grupos = [gerador(conexao, ano) for _, gerador in selecionados]

    return {
        "ano": ano,
        "grupos": grupos,
        "total_alertas": sum(grupo["total"] for grupo in grupos),
        "metodologia": (
            "Alertas são regras de triagem reproduzíveis aplicadas aos dados publicados. "
            "Eles não comprovam fraude, desperdício ou irregularidade."
        ),
        "limite_exibido_por_regra": LIMITE_RESULTADOS,
    }
