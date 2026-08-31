from sqlalchemy import text

from database import engine


with engine.connect() as conexao:
    pendentes = conexao.execute(text('''
        SELECT nome_origem, nome_normalizado
        FROM aliases_municipios
        WHERE fonte = 'repasses_goias' AND codigo_ibge IS NULL
        ORDER BY nome_origem
    ''')).mappings().all()
    duplicados = conexao.execute(text('''
        SELECT codigo_ibge, array_agg(nome_origem ORDER BY nome_origem) AS nomes,
               COUNT(*) AS quantidade
        FROM aliases_municipios
        WHERE fonte = 'repasses_goias' AND codigo_ibge IS NOT NULL
        GROUP BY codigo_ibge HAVING COUNT(*) > 1
    ''')).mappings().all()
    ausentes = conexao.execute(text('''
        SELECT m.codigo_ibge, m.nome
        FROM municipios_ibge m
        LEFT JOIN aliases_municipios a
          ON a.codigo_ibge = m.codigo_ibge AND a.fonte = 'repasses_goias'
        WHERE a.codigo_ibge IS NULL
        ORDER BY m.nome
    ''')).mappings().all()

print('Pendentes:', [dict(item) for item in pendentes])
print('Códigos com múltiplas grafias:', [dict(item) for item in duplicados])
print('Municípios IBGE sem correspondência:', [dict(item) for item in ausentes])
