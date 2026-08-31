from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from database import engine

router = APIRouter(prefix="/api/governador", tags=["governador"])

# O nome do cargo de Governador mudou de rótulo em 2020 (mesma pessoa, mesma função).
# As duas grafias precisam ser somadas para manter a série mensal contínua.
CARGOS_TITULAR = ["governador do estado", "governador - dse-1"]
TETO_CONSTITUCIONAL = 41650.92


@router.get("/resumo")
def resumo_governador():
    with engine.connect() as conexao:
        evolucao = conexao.execute(text("""
            SELECT DISTINCT ano_exercicio AS ano, mes_exercicio AS mes,
                   normalizar_texto_utf8(nome_servidor) AS nome,
                   valor_remuneracao_bruta AS bruto,
                   valor_remuneracao_liquida AS liquido
            FROM folha_pagamento
            WHERE LOWER(cargo) = ANY(:cargos)
            ORDER BY ano_exercicio, mes_exercicio
        """), {"cargos": CARGOS_TITULAR}).mappings().all()

        diarias_kpis = conexao.execute(text("""
            SELECT COUNT(*) AS viagens, COALESCE(SUM(valor_total), 0) AS total
            FROM diarias_passagens
            WHERE cargo ILIKE '%governador%' AND cargo NOT ILIKE '%vice%'
        """)).mappings().one()

        diarias_por_ano = conexao.execute(text("""
            SELECT ano_exercicio AS ano, COALESCE(SUM(valor_total), 0) AS valor, COUNT(*) AS viagens
            FROM diarias_passagens
            WHERE cargo ILIKE '%governador%' AND cargo NOT ILIKE '%vice%'
            GROUP BY ano_exercicio
            ORDER BY ano_exercicio
        """)).mappings().all()

    if not evolucao:
        raise HTTPException(status_code=404, detail="Nenhum registro de remuneração do Governador foi encontrado na folha de pagamento.")

    mandatos: list[dict] = []
    for linha in evolucao:
        marco = {"ano": linha["ano"], "mes": linha["mes"]}
        if not mandatos or mandatos[-1]["nome"] != linha["nome"]:
            mandatos.append({"nome": linha["nome"], "inicio": marco, "fim": marco})
        else:
            mandatos[-1]["fim"] = marco

    meses = len(evolucao)
    total_bruto = sum(float(linha["bruto"] or 0) for linha in evolucao)
    total_liquido = sum(float(linha["liquido"] or 0) for linha in evolucao)

    return {
        "kpis": {
            "meses_registrados": meses,
            "remuneracao_bruta_acumulada": total_bruto,
            "remuneracao_liquida_acumulada": total_liquido,
            "remuneracao_bruta_media_mensal": total_bruto / meses if meses else 0,
            "teto_constitucional": TETO_CONSTITUCIONAL,
        },
        "evolucao_mensal": [dict(linha) for linha in evolucao],
        "mandatos": mandatos,
        "diarias_governadoria": {
            "kpis": {
                "viagens": diarias_kpis["viagens"],
                "total": float(diarias_kpis["total"] or 0),
            },
            "por_ano": [dict(linha) for linha in diarias_por_ano],
        },
        "metodologia": (
            "A remuneração é obtida pelo cargo 'Governador do Estado' (e sua grafia atual "
            "'Governador - DSE-1') na folha de pagamento estadual, com linhas idênticas "
            "(mesmo ano, mês, cargo e valores) deduplicadas por DISTINCT, já que a fonte "
            "publica clones exatos de alguns lançamentos. As diárias apresentadas referem-se "
            "a cargos da estrutura da Governadoria (gabinete, ajudância de ordens, segurança), "
            "pois o Governador não possui lançamentos individuais de diária na fonte oficial; "
            "não devem ser lidas como viagens pessoais do titular do cargo."
        ),
    }
