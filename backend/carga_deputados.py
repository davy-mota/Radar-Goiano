import argparse
import hashlib
import io
import json
import zipfile

import pandas as pd
import requests
from sqlalchemy import text

from database import engine

URL_ZIP = 'https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip'

CAMPOS = {
    'nome_deputado': 'txNomeParlamentar',
    'partido': 'sgPartido',
    'categoria_despesa': 'txtDescricao',
    'fornecedor': 'txtFornecedor',
    'cnpj_cpf_fornecedor': 'txtCNPJCPF',
    'documento_id': 'ideDocumento',
    'url_documento': 'urlDocumento',
}
VALORES = {
    'valor_documento': 'vlrDocumento',
    'valor_glosa': 'vlrGlosa',
    'valor_liquido': 'vlrLiquido',
}


def valor_decimal(valor):
    texto_valor = str(valor or '').strip()
    if not texto_valor:
        return 0.0
    try:
        return float(texto_valor)
    except ValueError:
        return 0.0


def carregar(ano):
    url = URL_ZIP.format(ano=ano)
    conteudo_zip = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=180).content
    with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as pacote:
        nome_arquivo = pacote.namelist()[0]
        with pacote.open(nome_arquivo) as arquivo:
            frame = pd.read_csv(arquivo, sep=';', dtype=str, encoding='utf-8-sig').fillna('')

    obrigatorios = {'sgUF', 'ideCadastro', 'numMes', 'numAno', *CAMPOS.values(), *VALORES.values()}
    ausentes = obrigatorios.difference(frame.columns)
    if ausentes:
        raise ValueError(f'Colunas obrigatórias ausentes: {sorted(ausentes)}')

    registros_fonte = len(frame)
    frame = frame[frame['sgUF'].str.strip() == 'GO'].copy()
    frame = frame[frame['ideCadastro'].str.strip() != ''].copy()
    registros_descartados = registros_fonte - len(frame)
    if frame.empty:
        raise ValueError(f'Nenhum registro de deputado de Goiás encontrado para {ano}.')

    recurso_meta = {'url': url, 'formato': 'csv.zip'}
    with engine.begin() as conexao:
        lote = conexao.execute(text('''
            INSERT INTO lotes_deputados(status, ano, recurso)
            VALUES ('preparando', :ano, CAST(:recurso AS jsonb)) RETURNING id
        '''), {'ano': ano, 'recurso': json.dumps(recurso_meta)}).scalar_one()

    try:
        itens = []
        for linha in frame.to_dict('records'):
            item = {'lote_id': lote, 'ano': ano, 'mes': int(linha['numMes']) if linha['numMes'] else None}
            item['deputado_id'] = int(linha['ideCadastro'])
            item.update({destino: str(linha[origem]).strip() for destino, origem in CAMPOS.items()})
            item.update({destino: valor_decimal(linha[origem]) for destino, origem in VALORES.items()})
            item['data_documento'] = (
                pd.to_datetime(linha['datEmissao'], format='mixed').date()
                if linha.get('datEmissao') else None
            )
            item['chave_conteudo'] = hashlib.sha256(
                json.dumps(item, sort_keys=True, default=str, ensure_ascii=False).encode('utf-8')
            ).hexdigest()
            itens.append(item)

        colunas = list(itens[0])
        inserir = text(f'''INSERT INTO fatos_despesas_deputados({",".join(colunas)})
            VALUES({",".join(":" + coluna for coluna in colunas)}) ON CONFLICT DO NOTHING''')
        with engine.begin() as conexao:
            for inicio in range(0, len(itens), 1000):
                conexao.execute(inserir, itens[inicio:inicio + 1000])

            metricas = dict(conexao.execute(text('''
                SELECT COUNT(*) registros, COUNT(DISTINCT deputado_id) deputados,
                       SUM(valor_liquido) liquido
                FROM fatos_despesas_deputados WHERE lote_id = :lote
            '''), {'lote': lote}).mappings().one())
            metricas['registros_fonte'] = registros_fonte
            metricas['registros_descartados_fora_go'] = registros_descartados
            if not metricas['registros'] or not metricas['liquido']:
                raise ValueError('Carga sem registros ou sem valor líquido.')

            conexao.execute(text('''
                UPDATE lotes_deputados SET status = 'arquivado'
                WHERE status = 'ativo' AND ano = :ano
            '''), {'ano': ano})
            conexao.execute(text('''
                UPDATE lotes_deputados SET status = 'ativo', finalizado_em = now(), metricas = CAST(:m AS jsonb)
                WHERE id = :lote
            '''), {'lote': lote, 'm': json.dumps(metricas, default=float)})
        return lote, metricas
    except Exception as erro:
        with engine.begin() as conexao:
            conexao.execute(text('''
                UPDATE lotes_deputados SET status = 'rejeitado', observacao = :erro WHERE id = :lote
            '''), {'lote': lote, 'erro': str(erro)})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Carrega despesas de deputados federais de Goiás (CEAP).')
    parser.add_argument('--ano', type=int, required=True)
    argumentos = parser.parse_args()
    print(carregar(argumentos.ano))
