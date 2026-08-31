import argparse
import hashlib
import io
import json

import pandas as pd
import requests
from sqlalchemy import text

from carga_populacao_ibge import normalizar_nome
from database import engine

CKAN = 'https://dadosabertos.go.gov.br/api/3/action/package_show'

CAMPOS = {
    'orgao': 'Órgão Sucessor Atual (Código/Nome)',
    'processo': 'PROCESSO',
    'natureza_codigo': 'Natureza Despesa (Codigo)',
    'natureza_nome': 'Natureza Despesa (Nome)',
    'funcao': 'Função (Nome)',
    'subfuncao': 'SubFunção (Nome)',
    'empenho_sequencial': 'Empenho (Sequencial)',
    'descricao': 'Descrição Despesa',
    'historico': 'Empenho (Histórico)',
    'numero_emenda': 'Número Emenda',
    'autor': 'Autor (Deputado)',
    'objeto': 'Objeto',
    'municipio_origem': 'Município (Beneficiário)',
    'beneficiario': 'Beneficiário (Nome)',
    'cnpj': 'CNPJ',
    'numero_pdf': 'Número PDF',
    'tipo_emenda': 'Tipo Emenda',
    'grupo_despesa': 'Grupo Despesa',
}
VALORES = {
    'valor_indicado': 'PDF (Valor Parcela)',
    'valor_empenhado': 'Valor Empenho',
    'valor_liquidado': 'Liquidação (Saldo)',
    'valor_pago': 'OP (Saldo)',
}


def valor_decimal(valor):
    texto_valor = str(valor or '').strip()
    if not texto_valor:
        return 0.0
    if ',' in texto_valor:
        texto_valor = texto_valor.replace('.', '').replace(',', '.')
    try:
        return float(texto_valor)
    except ValueError:
        return 0.0


def carregar(ano):
    pacote = requests.get(CKAN, params={'id': 'emendas-parlamentares'}, timeout=60).json()['result']
    recursos = [recurso for recurso in pacote['resources']
                if recurso.get('format', '').upper() == 'CSV' and str(ano) in recurso.get('name', '')]
    if len(recursos) != 1:
        raise ValueError(f'Esperado um CSV independente para {ano}; encontrados {len(recursos)}.')
    recurso = recursos[0]
    conteudo = requests.get(recurso['url'], timeout=180).content
    frame = pd.read_csv(io.BytesIO(conteudo), sep='\t', dtype=str, encoding='utf-8').fillna('')
    obrigatorios = {'Exercício (Ano)', 'Data', 'Data Atualização', *CAMPOS.values(), *VALORES.values()}
    ausentes = obrigatorios.difference(frame.columns)
    if ausentes:
        raise ValueError(f'Colunas obrigatórias ausentes: {sorted(ausentes)}')
    registros_fonte = len(frame)
    frame = frame[frame['Exercício (Ano)'].astype(str).str.strip() == str(ano)].copy()
    registros_descartados = registros_fonte - len(frame)
    if frame.empty:
        raise ValueError(f'O arquivo não contém registros do exercício {ano}.')
    valores_invalidos = sum(
        1 for coluna in VALORES.values() for valor in frame[coluna]
        if str(valor).strip() and str(valor).strip().upper() in {'#N/D', '#N/A', 'N/D', 'N/A'}
    )

    recurso_meta = {'id': recurso['id'], 'nome': recurso['name'], 'url': recurso['url']}
    with engine.begin() as conexao:
        lote = conexao.execute(text('''
            INSERT INTO lotes_emendas(status,ano,recurso)
            VALUES ('preparando',:ano,CAST(:recurso AS jsonb)) RETURNING id
        '''), {'ano': ano, 'recurso': json.dumps(recurso_meta)}).scalar_one()

    try:
        itens = []
        for linha in frame.to_dict('records'):
            item = {'lote_id': lote, 'ano': ano}
            item.update({destino: str(linha[origem]).strip() for destino, origem in CAMPOS.items()})
            item.update({destino: valor_decimal(linha[origem]) for destino, origem in VALORES.items()})
            item['data'] = pd.to_datetime(linha['Data'], format='mixed', dayfirst=True).date()
            item['data_atualizacao'] = pd.to_datetime(
                linha['Data Atualização'], format='mixed', dayfirst=True
            ).date()
            item['chave_conteudo'] = hashlib.sha256(
                json.dumps(item, sort_keys=True, default=str, ensure_ascii=False).encode('utf-8')
            ).hexdigest()
            itens.append(item)

        colunas = list(itens[0])
        inserir = text(f'''INSERT INTO fatos_emendas({','.join(colunas)})
            VALUES({','.join(':' + coluna for coluna in colunas)}) ON CONFLICT DO NOTHING''')
        with engine.begin() as conexao:
            for inicio in range(0, len(itens), 1000):
                conexao.execute(inserir, itens[inicio:inicio + 1000])

            municipios_ibge = conexao.execute(text('SELECT codigo_ibge,nome FROM municipios_ibge')).mappings()
            nomes = {}
            for municipio in municipios_ibge:
                nomes.setdefault(normalizar_nome(municipio['nome']), []).append(municipio['codigo_ibge'])
            origens = conexao.execute(text('''
                SELECT DISTINCT municipio_origem FROM fatos_emendas WHERE lote_id=:lote
            '''), {'lote': lote}).scalars()
            for origem in origens:
                normalizado = normalizar_nome(origem)
                candidatos = nomes.get(normalizado, [])
                codigo = candidatos[0] if len(candidatos) == 1 else None
                conexao.execute(text('''
                    INSERT INTO aliases_municipios
                      (fonte,nome_origem,nome_normalizado,codigo_ibge,metodo,revisado_em)
                    VALUES ('emendas_goias',:origem,:normalizado,:codigo,:metodo,
                            CASE WHEN :codigo IS NOT NULL THEN now() END)
                    ON CONFLICT (fonte,nome_origem) DO UPDATE SET
                      nome_normalizado=EXCLUDED.nome_normalizado,
                      codigo_ibge=EXCLUDED.codigo_ibge,
                      metodo=EXCLUDED.metodo,
                      revisado_em=EXCLUDED.revisado_em
                '''), {'origem': origem, 'normalizado': normalizado, 'codigo': codigo,
                       'metodo': 'exato_normalizado' if codigo else 'pendente'})

            metricas = dict(conexao.execute(text('''
                SELECT COUNT(*) registros,SUM(valor_indicado) indicado,
                 SUM(valor_empenhado) empenhado,SUM(valor_liquidado) liquidado,
                 SUM(valor_pago) pago
                FROM fatos_emendas WHERE lote_id=:lote
            '''), {'lote': lote}).mappings().one())
            metricas['registros_fonte'] = registros_fonte
            metricas['registros_descartados_outros_exercicios'] = registros_descartados
            metricas['valores_monetarios_invalidos'] = valores_invalidos
            if metricas['registros'] == 0 or metricas['empenhado'] == 0:
                raise ValueError('Carga sem registros ou sem valor empenhado.')
            conexao.execute(text("UPDATE lotes_emendas SET status='arquivado' WHERE status='ativo'"))
            conexao.execute(text('''
                UPDATE lotes_emendas SET status='ativo',finalizado_em=now(),metricas=CAST(:m AS jsonb)
                WHERE id=:lote
            '''), {'lote': lote, 'm': json.dumps(metricas, default=float)})
        return lote, metricas
    except Exception as erro:
        with engine.begin() as conexao:
            conexao.execute(text('''
                UPDATE lotes_emendas SET status='rejeitado',observacao=:erro WHERE id=:lote
            '''), {'lote': lote, 'erro': str(erro)})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ano', type=int, required=True)
    argumentos = parser.parse_args()
    print(carregar(argumentos.ano))
