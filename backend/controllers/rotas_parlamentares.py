from fastapi import APIRouter, Query
from sqlalchemy import text

from database import engine

router = APIRouter(prefix='/api/parlamentares', tags=['Despesas parlamentares'])


@router.get('/resumo')
def resumo(ano: int = Query(..., ge=2008, le=2100)):
    parametros = {'ano': ano}
    with engine.connect() as conexao:
        parlamentares = [dict(item) for item in conexao.execute(text('''
            WITH totais AS (
              SELECT cargo,parlamentar_codigo,parlamentar_nome,MAX(partido) partido,
                COUNT(*) documentos,COUNT(DISTINCT mes) meses_com_registro,
                SUM(valor_documento) valor_documentos,SUM(valor_glosa) glosas,
                SUM(valor_reembolsado) reembolsado,
                SUM(valor_reembolsado)/COUNT(DISTINCT mes) media_mensal,
                MAX(valor_reembolsado) maior_documento
              FROM vw_despesas_parlamentares_ativas WHERE ano=:ano
              GROUP BY 1,2,3
            ),mensais AS (
              SELECT cargo,parlamentar_codigo,mes,SUM(valor_reembolsado) total_mes
              FROM vw_despesas_parlamentares_ativas WHERE ano=:ano GROUP BY 1,2,3
            ),picos AS (
              SELECT cargo,parlamentar_codigo,MAX(total_mes) maior_mes FROM mensais GROUP BY 1,2
            ),estatisticas AS (
              SELECT cargo,COUNT(*) tamanho_coorte,AVG(media_mensal) media_coorte,
                percentile_cont(.5) WITHIN GROUP (ORDER BY media_mensal) mediana_coorte
              FROM totais GROUP BY cargo
            ),ranqueados AS (
              SELECT t.*,RANK() OVER(PARTITION BY cargo ORDER BY media_mensal DESC) posicao,
                PERCENT_RANK() OVER(PARTITION BY cargo ORDER BY media_mensal) percentil
              FROM totais t
            )
            SELECT r.*,e.tamanho_coorte,e.media_coorte,e.mediana_coorte,p.maior_mes,
              r.media_mensal/e.mediana_coorte razao_mediana,
              p.maior_mes/r.media_mensal razao_pico_mensal
            FROM ranqueados r JOIN estatisticas e USING(cargo)
            JOIN picos p USING(cargo,parlamentar_codigo)
            ORDER BY cargo,r.media_mensal DESC
        '''), parametros).mappings()]
        categorias = [dict(item) for item in conexao.execute(text('''
            WITH categorias AS (
              SELECT cargo,parlamentar_codigo,categoria,SUM(valor_reembolsado) valor,
                ROW_NUMBER() OVER(PARTITION BY cargo,parlamentar_codigo
                  ORDER BY SUM(valor_reembolsado) DESC) ordem,
                SUM(SUM(valor_reembolsado)) OVER(PARTITION BY cargo,parlamentar_codigo) total
              FROM vw_despesas_parlamentares_ativas WHERE ano=:ano
              GROUP BY 1,2,3
            )
            SELECT cargo,parlamentar_codigo,categoria categoria_principal,valor valor_categoria,
              valor/NULLIF(total,0) concentracao_categoria
            FROM categorias WHERE ordem=1
        '''), parametros).mappings()]
        cobertura = [dict(item) for item in conexao.execute(text('''
            SELECT p.cargo,COUNT(DISTINCT p.parlamentar_codigo) cadastrados,
              COUNT(DISTINCT f.parlamentar_codigo) com_registros,
              COUNT(DISTINCT p.parlamentar_codigo)-COUNT(DISTINCT f.parlamentar_codigo) sem_registros
            FROM parlamentares_lote p
            JOIN lotes_despesas_parlamentares l ON l.id=p.lote_id AND l.status='ativo'
            LEFT JOIN fatos_despesas_parlamentares f ON f.lote_id=p.lote_id
              AND f.cargo=p.cargo AND f.parlamentar_codigo=p.parlamentar_codigo
            WHERE l.ano=:ano GROUP BY p.cargo
        '''), parametros).mappings()]
        sem_registros = [dict(item) for item in conexao.execute(text('''
            SELECT p.cargo,p.parlamentar_codigo,p.parlamentar_nome,p.partido
            FROM parlamentares_lote p
            JOIN lotes_despesas_parlamentares l ON l.id=p.lote_id AND l.status='ativo'
            LEFT JOIN fatos_despesas_parlamentares f ON f.lote_id=p.lote_id
              AND f.cargo=p.cargo AND f.parlamentar_codigo=p.parlamentar_codigo
            WHERE l.ano=:ano AND f.id IS NULL ORDER BY p.cargo,p.parlamentar_nome
        '''), parametros).mappings()]
        totais = [dict(item) for item in conexao.execute(text('''
            SELECT cargo,COUNT(*) documentos,SUM(valor_reembolsado) reembolsado,
              SUM(valor_glosa) glosas,COUNT(DISTINCT categoria) categorias
            FROM vw_despesas_parlamentares_ativas WHERE ano=:ano GROUP BY cargo
        '''), parametros).mappings()]

    categorias_indice = {
        (item['cargo'], item['parlamentar_codigo']): item for item in categorias
    }
    for parlamentar in parlamentares:
        parlamentar.update(categorias_indice.get(
            (parlamentar['cargo'], parlamentar['parlamentar_codigo']), {}
        ))
    return {
        'ano': ano, 'parlamentares': parlamentares, 'cobertura': cobertura,
        'sem_registros': sem_registros, 'totais': totais,
        'fontes': {
            'deputado_federal': 'Câmara dos Deputados — CEAP',
            'deputado_estadual': 'Assembleia Legislativa de Goiás — Verba Indenizatória',
            'senador': 'Senado Federal — CEAPS',
        },
        'indisponiveis': [
            {'cargo': 'vereador', 'motivo': 'Não existe fonte centralizada para as 246 Câmaras Municipais de Goiás.'},
        ],
    }
