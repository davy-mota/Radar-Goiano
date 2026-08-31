from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from database import engine
from .sql_utils import DOCUMENTO_CREDOR_NORMALIZADO, ORGAO_NORMALIZADO


router = APIRouter(prefix="/api/fornecedores", tags=["fornecedores"])

DOC_CONTRATO = """
CASE
    WHEN cnpj_cpf_contratado ~ '^[0-9.\\/-]+$'
     AND length(regexp_replace(cnpj_cpf_contratado, '[^0-9]', '', 'g')) BETWEEN 12 AND 14
    THEN lpad(regexp_replace(cnpj_cpf_contratado, '[^0-9]', '', 'g'), 14, '0')
END
"""


def validar_cnpj(documento: str) -> str:
    cnpj = "".join(caractere for caractere in documento if caractere.isdigit())
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        raise HTTPException(status_code=422, detail="CNPJ inválido.")

    def digito(base: str, pesos: list[int]) -> str:
        soma = sum(int(numero) * peso for numero, peso in zip(base, pesos))
        resto = soma % 11
        return str(0 if resto < 2 else 11 - resto)

    primeiro = digito(cnpj[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    segundo = digito(cnpj[:12] + primeiro, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    if cnpj[-2:] != primeiro + segundo:
        raise HTTPException(status_code=422, detail="CNPJ inválido.")
    return cnpj


def _somar(conexao, tabela: str, coluna_valor: str, parametros: dict):
    return conexao.execute(
        text(f"SELECT COALESCE(SUM({coluna_valor}), 0) FROM {tabela} WHERE {DOCUMENTO_CREDOR_NORMALIZADO} = :cnpj"),
        parametros,
    ).scalar_one()


@router.get("/{documento}/resumo")
def resumo_fornecedor(documento: str):
    cnpj = validar_cnpj(documento)
    parametros = {"cnpj": cnpj}

    with engine.connect() as conexao:
        kpis = dict(conexao.execute(text(f"""
            SELECT COUNT(*) AS pagamentos,
                   COUNT(DISTINCT nome_orgao) AS orgaos,
                   MIN(ano_exercicio) AS primeiro_ano,
                   MAX(ano_exercicio) AS ultimo_ano,
                   COALESCE(SUM(valor_pago), 0) AS pago
            FROM vw_pagamentos_ativos
            WHERE {DOCUMENTO_CREDOR_NORMALIZADO} = :cnpj
        """), parametros).mappings().one())
        kpis["empenhado"] = _somar(conexao, "vw_empenhos_ativos", "valor_empenhado", parametros)
        kpis["liquidado"] = _somar(conexao, "vw_liquidacoes_ativas", "valor_liquidado", parametros)

        nomes = conexao.execute(text(f"""
            SELECT nome_credor AS nome, COUNT(*) AS ocorrencias,
                   COALESCE(SUM(valor_pago), 0) AS valor_pago
            FROM vw_pagamentos_ativos
            WHERE {DOCUMENTO_CREDOR_NORMALIZADO} = :cnpj AND nome_credor IS NOT NULL
            GROUP BY nome_credor
            ORDER BY ocorrencias DESC, valor_pago DESC
            LIMIT 5
        """), parametros).mappings().all()

        def _por_ano(tabela: str, coluna_valor: str, rotulo: str) -> dict[int, float]:
            linhas = conexao.execute(text(f"""
                SELECT ano_exercicio AS ano, COALESCE(SUM({coluna_valor}), 0) AS valor
                FROM {tabela} WHERE {DOCUMENTO_CREDOR_NORMALIZADO} = :cnpj GROUP BY ano_exercicio
            """), parametros).mappings().all()
            return {linha["ano"]: linha["valor"] for linha in linhas}

        empenhado_por_ano = _por_ano("vw_empenhos_ativos", "valor_empenhado", "empenhado")
        liquidado_por_ano = _por_ano("vw_liquidacoes_ativas", "valor_liquidado", "liquidado")
        pago_por_ano = _por_ano("vw_pagamentos_ativos", "valor_pago", "pago")
        anos_relacionados = sorted(set(empenhado_por_ano) | set(liquidado_por_ano) | set(pago_por_ano))
        evolucao = [
            {
                "ano": ano,
                "empenhado": empenhado_por_ano.get(ano, 0),
                "liquidado": liquidado_por_ano.get(ano, 0),
                "pago": pago_por_ano.get(ano, 0),
            }
            for ano in anos_relacionados
        ]

        orgaos = conexao.execute(text(f"""
            SELECT {ORGAO_NORMALIZADO} AS nome, COUNT(*) AS pagamentos,
                   COALESCE(SUM(valor_pago), 0) AS valor
            FROM vw_pagamentos_ativos
            WHERE {DOCUMENTO_CREDOR_NORMALIZADO} = :cnpj
            GROUP BY {ORGAO_NORMALIZADO}
            ORDER BY valor DESC
            LIMIT 10
        """), parametros).mappings().all()
        contratos = conexao.execute(text(f"""
            SELECT COUNT(*) AS quantidade,
                   COALESCE(SUM(valor_contrato), 0) AS valor_total
            FROM contratos_licitacoes
            WHERE {DOC_CONTRATO} = :cnpj
        """), parametros).mappings().one()

    if not kpis["pagamentos"] and not contratos["quantidade"]:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")

    return {
        "cnpj": cnpj,
        "nome_principal": nomes[0]["nome"] if nomes else "Fornecedor sem nome informado",
        "nomes_encontrados": [dict(item) for item in nomes],
        "kpis": kpis,
        "contratos": dict(contratos),
        "evolucao_anual": evolucao,
        "top_orgaos": [dict(item) for item in orgaos],
        "metodologia": "Associação por CNPJ normalizado e validado; nomes não são usados como chave.",
    }


@router.get("/{documento}/pagamentos")
def pagamentos_fornecedor(
    documento: str,
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, ge=10, le=100),
):
    cnpj = validar_cnpj(documento)
    parametros = {"cnpj": cnpj, "limite": por_pagina, "offset": (pagina - 1) * por_pagina}
    with engine.connect() as conexao:
        linhas = conexao.execute(text(f"""
            SELECT id AS id_registro, numero_empenho, ano_exercicio, mes AS mes_exercicio,
                   {ORGAO_NORMALIZADO} AS nome_orgao, nome_credor, data_pagamento AS data_emissao,
                   descricao, valor_pago,
                   COUNT(*) OVER() AS total_registros
            FROM vw_pagamentos_ativos
            WHERE {DOCUMENTO_CREDOR_NORMALIZADO} = :cnpj
            ORDER BY data_pagamento DESC NULLS LAST, id DESC
            LIMIT :limite OFFSET :offset
        """), parametros).mappings().all()

    total = linhas[0]["total_registros"] if linhas else 0
    itens = []
    for linha in linhas:
        item = dict(linha)
        item.pop("total_registros")
        itens.append(item)
    return {
        "itens": itens,
        "paginacao": {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total,
            "total_paginas": (total + por_pagina - 1) // por_pagina,
        },
    }


@router.get("/{documento}/contratos")
def contratos_fornecedor(documento: str):
    cnpj = validar_cnpj(documento)
    with engine.connect() as conexao:
        linhas = conexao.execute(text(f"""
            SELECT id, ano_exercicio, nome_orgao, numero_contrato,
                   nome_contratado, objeto_contrato, modalidade_licitacao,
                   valor_contrato, data_assinatura
            FROM contratos_licitacoes
            WHERE {DOC_CONTRATO} = :cnpj
            ORDER BY data_assinatura DESC NULLS LAST, valor_contrato DESC
            LIMIT 100
        """), {"cnpj": cnpj}).mappings().all()
    return {"itens": [dict(item) for item in linhas], "limite": 100}
