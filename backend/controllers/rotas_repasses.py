from fastapi import APIRouter,HTTPException,Query
from sqlalchemy import text
from database import engine
router=APIRouter(prefix='/api/repasses',tags=['Repasses municipais'])
@router.get('/resumo')
def resumo(ano:int=Query(...,ge=2014,le=2100)):
 with engine.connect() as c:
  k=dict(c.execute(text("SELECT COUNT(*) registros,COUNT(DISTINCT mes) meses,COUNT(DISTINCT codigo_ibge) municipios,COUNT(*) FILTER (WHERE codigo_ibge IS NULL) registros_sem_municipio,SUM(credito_icms) icms,SUM(credito_ipi) ipi,SUM(credito_ipva) ipva,SUM(credito_icms+credito_ipi+credito_ipva) total,SUM(deducao_icms+deducao_ipi+deducao_ipva) fundeb,MAX(populacao) FILTER (WHERE populacao IS NOT NULL) populacao_maxima FROM vw_repasses_municipais_canonicos WHERE ano=:a"),{'a':ano}).mappings().one())
  top=[dict(x) for x in c.execute(text("SELECT municipio_canonico nome,codigo_ibge,MAX(populacao) populacao,SUM(credito_icms+credito_ipi+credito_ipva) valor,SUM(credito_icms+credito_ipi+credito_ipva)/MAX(populacao) valor_per_capita FROM vw_repasses_municipais_canonicos WHERE ano=:a AND codigo_ibge IS NOT NULL GROUP BY 1,2 ORDER BY valor DESC LIMIT 15"),{'a':ano}).mappings()]
  per_capita=[dict(x) for x in c.execute(text("SELECT municipio_canonico nome,codigo_ibge,MAX(populacao) populacao,SUM(credito_icms+credito_ipi+credito_ipva) valor,SUM(credito_icms+credito_ipi+credito_ipva)/MAX(populacao) valor_per_capita FROM vw_repasses_municipais_canonicos WHERE ano=:a AND populacao IS NOT NULL GROUP BY 1,2 ORDER BY valor_per_capita DESC LIMIT 15"),{'a':ano}).mappings()]
  mapa=[dict(x) for x in c.execute(text("SELECT municipio_canonico nome,codigo_ibge,MAX(populacao) populacao,SUM(credito_icms+credito_ipi+credito_ipva) valor,SUM(credito_icms+credito_ipi+credito_ipva)/MAX(populacao) valor_per_capita FROM vw_repasses_municipais_canonicos WHERE ano=:a AND codigo_ibge IS NOT NULL GROUP BY 1,2 ORDER BY 1"),{'a':ano}).mappings()]
  serie=[dict(x) for x in c.execute(text("SELECT mes,SUM(credito_icms) icms,SUM(credito_ipi) ipi,SUM(credito_ipva) ipva FROM vw_repasses_municipais_ativos WHERE ano=:a GROUP BY 1 ORDER BY 1"),{'a':ano}).mappings()]
 return {'ano':ano,'kpis':k,'ranking':top,'ranking_per_capita':per_capita,'mapa':mapa,'serie_mensal':serie,'cobertura':f"{k['meses']} meses publicados",'populacao_referencia':f"Estimativa IBGE em 1º de julho de {ano}"}

@router.get('/municipio/{codigo_ibge}')
def detalhe_municipio(codigo_ibge:int,ano:int=Query(...,ge=2014,le=2100)):
 with engine.connect() as c:
  detalhe=c.execute(text('''
   WITH totais AS (
    SELECT codigo_ibge,municipio_canonico nome,MAX(populacao) populacao,
     SUM(credito_icms) icms,SUM(credito_ipi) ipi,SUM(credito_ipva) ipva,
     SUM(deducao_icms+deducao_ipi+deducao_ipva) fundeb,
     SUM(credito_icms+credito_ipi+credito_ipva) total
    FROM vw_repasses_municipais_canonicos
    WHERE ano=:ano AND codigo_ibge IS NOT NULL GROUP BY 1,2
   ),posicoes AS (
    SELECT *,RANK() OVER(ORDER BY total DESC) posicao_total,
     RANK() OVER(ORDER BY total/populacao DESC) posicao_per_capita
    FROM totais
   )
   SELECT p.*,p.total/p.populacao valor_per_capita,m.regiao_imediata,m.regiao_intermediaria
   FROM posicoes p JOIN municipios_ibge m USING(codigo_ibge)
   WHERE p.codigo_ibge=:codigo
  '''),{'ano':ano,'codigo':codigo_ibge}).mappings().one_or_none()
  if not detalhe:raise HTTPException(status_code=404,detail='Município sem dados no exercício informado.')
  mensal=[dict(x) for x in c.execute(text('''
   SELECT mes,SUM(credito_icms) icms,SUM(credito_ipi) ipi,SUM(credito_ipva) ipva,
    SUM(credito_icms+credito_ipi+credito_ipva) total
   FROM vw_repasses_municipais_canonicos
   WHERE ano=:ano AND codigo_ibge=:codigo GROUP BY mes ORDER BY mes
  '''),{'ano':ano,'codigo':codigo_ibge}).mappings()]
  pares=[dict(x) for x in c.execute(text('''
   WITH totais AS (
    SELECT codigo_ibge,municipio_canonico nome,MAX(populacao) populacao,
     SUM(credito_icms+credito_ipi+credito_ipva) total
    FROM vw_repasses_municipais_canonicos
    WHERE ano=:ano AND codigo_ibge IS NOT NULL GROUP BY 1,2
   ),alvo AS (SELECT populacao FROM totais WHERE codigo_ibge=:codigo)
   SELECT t.codigo_ibge,t.nome,t.populacao,t.total,t.total/t.populacao valor_per_capita,
    (t.populacao-a.populacao)*100.0/a.populacao diferenca_populacao_percentual
   FROM totais t CROSS JOIN alvo a
   WHERE t.codigo_ibge<>:codigo
   ORDER BY ABS(t.populacao-a.populacao),t.nome LIMIT 5
  '''),{'ano':ano,'codigo':codigo_ibge}).mappings()]
 return {'ano':ano,'municipio':dict(detalhe),'serie_mensal':mensal,'municipios_semelhantes':pares,
  'cobertura':f"{len(mensal)} meses publicados"}
