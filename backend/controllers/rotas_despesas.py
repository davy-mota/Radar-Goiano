import csv
import io
from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from database import engine
from .sql_utils import (
    BUSCA_DESPESA_NORMALIZADA,
    ORGAO_NORMALIZADO,
    por_mes,
    serie_mensal_combinada,
)


router = APIRouter(prefix="/api/despesas", tags=["despesas"])

COLUNAS_ORDENACAO = {
    "valor_pago": "valor_pago",
    "data_emissao": "data_pagamento",
    "credor": "nome_credor",
    "orgao": ORGAO_NORMALIZADO,
}


def _filtros_sql(
    ano: str,
    mes: int | None = None,
    orgao: str | None = None,
    busca: str | None = None,
) -> tuple[str, dict]:
    condicoes = []
    parametros: dict = {}

    if ano != "todos":
        condicoes.append("ano_exercicio = :ano")
        parametros["ano"] = int(ano)
    if mes is not None:
        condicoes.append("mes = :mes")
        parametros["mes"] = mes
    if orgao:
        condicoes.append(f"{ORGAO_NORMALIZADO} = :orgao")
        parametros["orgao"] = orgao
    if busca:
        condicoes.append(f"{BUSCA_DESPESA_NORMALIZADA} ILIKE :busca")
        parametros["busca"] = f"%{busca.strip()}%"

    return (" WHERE " + " AND ".join(condicoes)) if condicoes else "", parametros


def _filtros_resumo_sql(
    ano: str,
    mes: int | None = None,
    orgao: str | None = None,
) -> tuple[str, dict]:
    """Monta filtros para a visao mensal, cujos orgaos ja estao normalizados."""
    condicoes = []
    parametros: dict = {}

    if ano != "todos":
        condicoes.append("ano_exercicio = :ano")
        parametros["ano"] = int(ano)
    if mes is not None:
        condicoes.append("mes = :mes")
        parametros["mes"] = mes
    if orgao:
        condicoes.append("nome_orgao = :orgao")
        parametros["orgao"] = orgao

    return (" WHERE " + " AND ".join(condicoes)) if condicoes else "", parametros


def _validar_ano(ano: str) -> str:
    if ano == "todos":
        return ano
    if not ano.isdigit() or not 2003 <= int(ano) <= 2100:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="Ano inválido.")
    return ano


def _celula_csv(valor) -> str:
    if valor is None:
        return ""
    texto = str(valor).replace("\r", " ").replace("\n", " ")
    if texto.startswith(("=", "+", "-", "@")):
        texto = "'" + texto
    return texto


def _documento_para_exportacao(documento) -> str:
    if not documento:
        return ""
    digitos = "".join(caractere for caractere in str(documento) if caractere.isdigit())
    if len(digitos) == 11:
        return "***.***.***-**"
    if 12 <= len(digitos) <= 14:
        return digitos.zfill(14)
    return ""


def _serie_com_total(
    conexao,
    tabela: str,
    coluna_valor: str,
    alias: str,
    where: str,
    parametros: dict,
    incluir_registros: bool = False,
):
    linhas = conexao.execute(text(f"""
        SELECT mes,
               COALESCE(SUM({coluna_valor}), 0) AS {alias}
        FROM {tabela}
        {where}
        GROUP BY mes
        ORDER BY mes
    """), parametros).mappings().all()
    total = sum((linha[alias] for linha in linhas), start=0)
    registros = 0
    if incluir_registros:
        registros = conexao.execute(
            text(f"SELECT COUNT(*) FROM {tabela} {where}"), parametros
        ).scalar_one()
    serie = por_mes({"mes": linha["mes"], alias: linha[alias]} for linha in linhas)
    return serie, total, registros


@router.get("/filtros")
def listar_filtros(ano: str = "2025"):
    ano = _validar_ano(ano)
    where, parametros = _filtros_resumo_sql(ano)
    with engine.connect() as conexao:
        anos = conexao.execute(text("""
            SELECT DISTINCT ano_exercicio
            FROM mv_despesas_execucao_mensal
            WHERE etapa = 'pago' AND ano_exercicio IS NOT NULL
            ORDER BY ano_exercicio DESC
        """)).scalars().all()
        orgaos = conexao.execute(text(f"""
            SELECT DISTINCT nome_orgao
            FROM mv_despesas_execucao_mensal
            {where}
              {"AND" if where else "WHERE"} etapa = 'pago' AND nome_orgao <> ''
            ORDER BY nome_orgao
        """), parametros).scalars().all()

    return {"anos": anos, "orgaos": orgaos}


@router.get("/resumo")
def resumo_despesas(
    ano: str = "2025",
    mes: int | None = Query(default=None, ge=1, le=12),
    orgao: str | None = None,
    busca: str | None = Query(default=None, max_length=120),
):
    ano = _validar_ano(ano)

    # A busca textual precisa consultar os registros individuais. Nos demais
    # casos, a visao mensal reduz milhoes de linhas a poucos milhares.
    if not busca or not busca.strip():
        where, parametros = _filtros_resumo_sql(ano, mes, orgao)
        with engine.connect() as conexao:
            linhas = conexao.execute(text(f"""
                SELECT etapa, mes,
                       COALESCE(SUM(valor), 0) AS valor,
                       COALESCE(SUM(registros), 0) AS registros
                FROM mv_despesas_execucao_mensal
                {where}
                GROUP BY etapa, mes
                ORDER BY etapa, mes
            """), parametros).mappings().all()

            where_top = where + (" AND" if where else " WHERE")
            top_orgaos = conexao.execute(text(f"""
                SELECT nome_orgao AS nome, COALESCE(SUM(valor), 0) AS valor
                FROM mv_despesas_execucao_mensal
                {where_top} etapa = 'pago' AND nome_orgao <> ''
                GROUP BY nome_orgao
                ORDER BY valor DESC
                LIMIT 5
            """), parametros).mappings().all()

        series = {"empenhado": {}, "liquidado": {}, "pago": {}}
        totais = {"empenhado": 0, "liquidado": 0, "pago": 0}
        registros = 0
        for linha in linhas:
            etapa = linha["etapa"]
            totais[etapa] += linha["valor"]
            series[etapa][linha["mes"]] = {
                "mes": linha["mes"],
                etapa: linha["valor"],
            }
            if etapa == "pago":
                registros += linha["registros"]

        dados_kpis = {
            "registros": registros,
            **totais,
            "a_pagar": totais["liquidado"] - totais["pago"],
        }
        return {
            "kpis": dados_kpis,
            "serie_mensal": serie_mensal_combinada(
                series["empenhado"], series["liquidado"], series["pago"]
            ),
            "top_orgaos": [dict(item) for item in top_orgaos],
        }

    where, parametros = _filtros_sql(ano, mes, orgao, busca)

    with engine.connect() as conexao:
        serie_empenhos, empenhado, _ = _serie_com_total(
            conexao, "vw_empenhos_ativos", "valor_empenhado", "empenhado", where, parametros
        )
        serie_liquidacoes, liquidado, _ = _serie_com_total(
            conexao, "vw_liquidacoes_ativas", "valor_liquidado", "liquidado", where, parametros
        )
        serie_pagamentos, pago, registros = _serie_com_total(
            conexao,
            "vw_pagamentos_ativos",
            "valor_pago",
            "pago",
            where,
            parametros,
            incluir_registros=True,
        )

        top_orgaos = conexao.execute(text(f"""
            SELECT {ORGAO_NORMALIZADO} AS nome, COALESCE(SUM(valor_pago), 0) AS valor
            FROM vw_pagamentos_ativos
            {where}
            GROUP BY {ORGAO_NORMALIZADO}
            ORDER BY valor DESC
            LIMIT 5
        """), parametros).mappings().all()

    dados_kpis = {
        "registros": registros,
        "empenhado": empenhado,
        "liquidado": liquidado,
        "pago": pago,
        "a_pagar": liquidado - pago,
    }
    return {
        "kpis": dados_kpis,
        "serie_mensal": serie_mensal_combinada(serie_empenhos, serie_liquidacoes, serie_pagamentos),
        "top_orgaos": [dict(item) for item in top_orgaos],
    }


@router.get("/exportar.csv")
def exportar_despesas(
    ano: str = "2025",
    mes: int | None = Query(default=None, ge=1, le=12),
    orgao: str | None = None,
    busca: str | None = Query(default=None, max_length=120),
    limite: int = Query(default=10_000, ge=1, le=10_000),
):
    ano = _validar_ano(ano)
    where, parametros = _filtros_sql(ano, mes, orgao, busca)
    parametros["limite"] = limite
    consulta = text(f"""
        SELECT numero_empenho, ano_exercicio, mes,
               {ORGAO_NORMALIZADO} AS nome_orgao,
               documento_credor, nome_credor, data_pagamento,
               valor_pago
        FROM vw_pagamentos_ativos
        {where}
        ORDER BY valor_pago DESC NULLS LAST, id DESC
        LIMIT :limite
    """)
    cabecalho = [
        "numero_empenho", "ano", "mes", "orgao", "documento_favorecido",
        "favorecido", "data_pagamento", "valor_pago",
    ]

    def gerar_csv():
        buffer = io.StringIO()
        escritor = csv.writer(buffer, delimiter=";", lineterminator="\n")
        escritor.writerow(cabecalho)
        yield "﻿" + buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)

        with engine.connect() as conexao:
            resultado = conexao.execution_options(stream_results=True).execute(consulta, parametros)
            for lote in resultado.partitions(500):
                for linha in lote:
                    valores = list(linha)
                    valores[4] = _documento_para_exportacao(valores[4])
                    escritor.writerow([_celula_csv(valor) for valor in valores])
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)

    nome = f"radar_goiano_despesas_{ano}.csv"
    return StreamingResponse(
        gerar_csv(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{nome}"',
            "X-Export-Limit": str(limite),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("")
def listar_despesas(
    ano: str = "2025",
    mes: int | None = Query(default=None, ge=1, le=12),
    orgao: str | None = None,
    busca: str | None = Query(default=None, max_length=120),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=25, ge=10, le=100),
    ordenar_por: Literal["valor_pago", "data_emissao", "credor", "orgao"] = "valor_pago",
    direcao: Literal["asc", "desc"] = "desc",
):
    ano = _validar_ano(ano)
    where, parametros = _filtros_sql(ano, mes, orgao, busca)
    parametros.update({"limite": por_pagina, "offset": (pagina - 1) * por_pagina})
    coluna = COLUNAS_ORDENACAO[ordenar_por]

    with engine.connect() as conexao:
        total = conexao.execute(
            text(f"SELECT COUNT(*) FROM vw_pagamentos_ativos {where}"), parametros
        ).scalar_one()
        linhas = conexao.execute(text(f"""
            SELECT id AS id_registro, numero_empenho, ano_exercicio, mes AS mes_exercicio,
                   {ORGAO_NORMALIZADO} AS nome_orgao, documento_credor AS cnpj_cpf_credor,
                   nome_credor, data_pagamento AS data_emissao, valor_pago
            FROM vw_pagamentos_ativos
            {where}
            ORDER BY {coluna} {direcao.upper()} NULLS LAST, id DESC
            LIMIT :limite OFFSET :offset
        """), parametros).mappings().all()

    itens = [dict(linha) for linha in linhas]

    return {
        "itens": itens,
        "paginacao": {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total,
            "total_paginas": (total + por_pagina - 1) // por_pagina,
        },
    }
