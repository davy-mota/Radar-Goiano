from fastapi import APIRouter, Query
from sqlalchemy import text

from database import engine

router = APIRouter(prefix='/api/emendas', tags=['Emendas parlamentares'])


@router.get('/resumo')
def resumo(ano: int = Query(..., ge=2019, le=2100)):
    parametros = {'ano': ano}
    with engine.connect() as conexao:
        kpis = dict(conexao.execute(text('''
            SELECT COUNT(*) registros,COUNT(DISTINCT autor) autores,
              COUNT(DISTINCT funcao) funcoes,COUNT(DISTINCT beneficiario) beneficiarios,
              COUNT(DISTINCT codigo_ibge) municipios,
              COUNT(*) FILTER (WHERE codigo_ibge IS NULL) registros_sem_municipio,
              SUM(valor_indicado) indicado,SUM(valor_empenhado) empenhado,
              SUM(valor_liquidado) liquidado,SUM(valor_pago) pago,
              MAX(data_atualizacao) atualizado_em
            FROM vw_emendas_ativas WHERE ano=:ano
        '''), parametros).mappings().one())
        autores = [dict(item) for item in conexao.execute(text('''
            SELECT autor nome,SUM(valor_indicado) indicado,SUM(valor_empenhado) empenhado,
              SUM(valor_pago) pago,COUNT(*) registros
            FROM vw_emendas_ativas WHERE ano=:ano
            GROUP BY autor ORDER BY empenhado DESC LIMIT 12
        '''), parametros).mappings()]
        funcoes = [dict(item) for item in conexao.execute(text('''
            SELECT funcao nome,SUM(valor_empenhado) empenhado,SUM(valor_pago) pago,COUNT(*) registros
            FROM vw_emendas_ativas WHERE ano=:ano
            GROUP BY funcao ORDER BY empenhado DESC LIMIT 10
        '''), parametros).mappings()]
        municipios = [dict(item) for item in conexao.execute(text('''
            SELECT municipio_canonico nome,codigo_ibge,SUM(valor_empenhado) empenhado,
              SUM(valor_pago) pago,COUNT(*) registros
            FROM vw_emendas_ativas WHERE ano=:ano AND codigo_ibge IS NOT NULL
            GROUP BY municipio_canonico,codigo_ibge ORDER BY empenhado DESC LIMIT 15
        '''), parametros).mappings()]
        registros = [dict(item) for item in conexao.execute(text('''
            SELECT autor,objeto,beneficiario,municipio_origem,funcao,tipo_emenda,
              valor_indicado,valor_empenhado,valor_liquidado,valor_pago
            FROM vw_emendas_ativas WHERE ano=:ano
            ORDER BY valor_empenhado DESC,autor LIMIT 20
        '''), parametros).mappings()]
        lote = conexao.execute(text('''
            SELECT id,metricas,recurso,finalizado_em FROM lotes_emendas
            WHERE status='ativo' AND ano=:ano
        '''), parametros).mappings().one_or_none()
    return {
        'ano': ano, 'kpis': kpis, 'autores': autores, 'funcoes': funcoes,
        'municipios': municipios, 'registros': registros,
        'qualidade': dict(lote) if lote else None,
        'cobertura': 'Arquivo oficial publicado como 2025, com dados filtrados pelo exercício',
    }
