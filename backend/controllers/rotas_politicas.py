from fastapi import APIRouter, Query
from sqlalchemy import text
from database import engine

router = APIRouter(prefix="/api/politicas", tags=["Políticas públicas"])

@router.get("/anos")
def anos():
    with engine.connect() as c:
        return {"anos": list(c.execute(text("SELECT DISTINCT ano_exercicio FROM vw_execucao_orcamentaria_ativa ORDER BY 1 DESC")).scalars())}

@router.get("/resumo")
def resumo(ano: int = Query(..., ge=2003, le=2100)):
    with engine.connect() as c:
        kpis = dict(c.execute(text("SELECT COALESCE(SUM(valor_empenhado),0) empenhado, COALESCE(SUM(valor_liquidado),0) liquidado, COALESCE(SUM(valor_pago),0) pago, COUNT(*) registros, COUNT(DISTINCT mes) meses FROM vw_execucao_orcamentaria_ativa WHERE ano_exercicio=:ano"), {"ano": ano}).mappings().one())
        def ranking(campo):
            return [dict(x) for x in c.execute(text(f"SELECT COALESCE({campo},'Não informado') nome, SUM(valor_pago) valor FROM vw_execucao_orcamentaria_ativa WHERE ano_exercicio=:ano GROUP BY 1 ORDER BY 2 DESC LIMIT 10"), {"ano": ano}).mappings()]
        funcoes = ranking("nome_funcao")
        grupos = ranking("nome_grupo")
        categorias = ranking("nome_categoria")
        serie = [dict(x) for x in c.execute(text("SELECT mes, SUM(valor_empenhado) empenhado, SUM(valor_liquidado) liquidado, SUM(valor_pago) pago FROM vw_execucao_orcamentaria_ativa WHERE ano_exercicio=:ano GROUP BY mes ORDER BY mes"), {"ano": ano}).mappings()]
    return {"ano": ano, "kpis": kpis, "funcoes": funcoes, "grupos": grupos, "categorias": categorias, "serie_mensal": serie, "metodologia": "Valores classificados pela função e natureza publicadas pela Secretaria da Economia."}
