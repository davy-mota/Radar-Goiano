import csv
import io
from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from database import engine
from .sql_utils import ORGAO_NORMALIZADO, por_mes, serie_mensal_combinada


router = APIRouter(prefix="/api/despesas", tags=["despesas"])

COLUNAS_ORDENACAO = {
    "valor_pago": "valor_pago",
    "data_emissao": "data_pagamento",
    "credor": "nome_credor",
    "orgao": "nome_orgao",
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
        condicoes.append("""
            (nome_credor ILIKE :busca
             OR documento_credor ILIKE :busca
             OR numero_empenho ILIKE :busca)
        """)
        parametros["busca"] = f"%{busca.strip()}%"

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


def _somar(conexao, tabela: str, coluna_valor: str, where: str, parametros: dict):
    return conexao.execute(
        text(f"SELECT COALESCE(SUM({coluna_valor}), 0) FROM {tabela} {where}"), parametros
    ).scalar_one()


@router.get("/filtros")
def listar_filtros(ano: str = "2025"):
    ano = _validar_ano(ano)
    where, parametros = _filtros_sql(ano)
    with engine.connect() as conexao:
        anos = conexao.execute(text("""
            SELECT DISTINCT ano_exercicio
            FROM vw_pagamentos_ativos
            WHERE ano_exercicio IS NOT NULL
            ORDER BY ano_exercicio DESC
        """)).scalars().all()
        orgaos = conexao.execute(text(f"""
            SELECT DISTINCT {ORGAO_NORMALIZADO} AS nome_orgao
            FROM vw_pagamentos_ativos
            {where}
              {"AND" if where else "WHERE"} nome_orgao IS NOT NULL
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
    where, parametros = _filtros_sql(ano, mes, orgao, busca)

    with engine.connect() as conexao:
        registros = conexao.execute(
            text(f"SELECT COUNT(*) FROM vw_pagamentos_ativos {where}"), parametros
        ).scalar_one()
        empenhado = _somar(conexao, "vw_empenhos_ativos", "valor_empenhado", where, parametros)
        liquidado = _somar(conexao, "vw_liquidacoes_ativas", "valor_liquidado", where, parametros)
        pago = _somar(conexao, "vw_pagamentos_ativos", "valor_pago", where, parametros)

        serie_empenhos = por_mes(conexao.execute(text(f"""
            SELECT mes, COALESCE(SUM(valor_empenhado), 0) AS empenhado
            FROM vw_empenhos_ativos {where} GROUP BY mes
        """), parametros).mappings().all())
        serie_liquidacoes = por_mes(conexao.execute(text(f"""
            SELECT mes, COALESCE(SUM(valor_liquidado), 0) AS liquidado
            FROM vw_liquidacoes_ativas {where} GROUP BY mes
        """), parametros).mappings().all())
        serie_pagamentos = por_mes(conexao.execute(text(f"""
            SELECT mes, COALESCE(SUM(valor_pago), 0) AS pago
            FROM vw_pagamentos_ativos {where} GROUP BY mes
        """), parametros).mappings().all())

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
        linhas = conexao.execute(text(f"""
            SELECT id AS id_registro, numero_empenho, ano_exercicio, mes AS mes_exercicio,
                   {ORGAO_NORMALIZADO} AS nome_orgao, documento_credor AS cnpj_cpf_credor,
                   nome_credor, data_pagamento AS data_emissao, valor_pago,
                   COUNT(*) OVER() AS total_registros
            FROM vw_pagamentos_ativos
            {where}
            ORDER BY {coluna} {direcao.upper()} NULLS LAST, id DESC
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
