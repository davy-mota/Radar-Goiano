import argparse
import hashlib
import io
import json
import unicodedata

import pandas as pd
import requests
from sqlalchemy import text

from database import engine

CAMARA_URL = 'https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip'
SENADO_CEAPS_URL = (
    'https://adm.senado.gov.br/adm-dadosabertos/api/v1/'
    'senadores/despesas_ceaps/{ano}/csv'
)
SENADORES_URL = 'https://legis.senado.leg.br/dadosabertos/senador/lista/legislatura/57'
ALEGO_API = 'https://transparencia.al.go.leg.br/api/transparencia/verbas_indenizatorias'


def normalizar(valor):
    return ''.join(
        caractere for caractere in unicodedata.normalize('NFKD', str(valor or '').upper())
        if not unicodedata.combining(caractere)
    ).strip()


def decimal(valor):
    texto_valor = str(valor or '').strip()
    if not texto_valor:
        return 0.0
    if ',' in texto_valor:
        texto_valor = texto_valor.replace('.', '').replace(',', '.')
    return float(texto_valor)


def chave(item):
    conteudo = {campo: valor for campo, valor in item.items() if campo != 'lote_id'}
    return hashlib.sha256(
        json.dumps(conteudo, sort_keys=True, default=str, ensure_ascii=False).encode('utf-8')
    ).hexdigest()


def obter_senadores_goias():
    resposta = requests.get(SENADORES_URL, headers={'Accept': 'application/json'}, timeout=90).json()
    parlamentares = resposta['ListaParlamentarLegislatura']['Parlamentares']['Parlamentar']
    resultado = {}
    for parlamentar in parlamentares:
        identificacao = parlamentar['IdentificacaoParlamentar']
        if identificacao.get('UfParlamentar') == 'GO':
            resultado[normalizar(identificacao['NomeParlamentar'])] = identificacao
    if len(resultado) < 3:
        raise ValueError(f'Esperados ao menos três senadores de Goiás; recebidos {len(resultado)}.')
    return resultado


def ler_camara(ano, lote):
    conteudo = requests.get(CAMARA_URL.format(ano=ano), timeout=180).content
    frame = pd.read_csv(io.BytesIO(conteudo), compression='zip', sep=';', dtype=str, encoding='utf-8').fillna('')
    frame = frame[(frame['sgUF'] == 'GO') & (frame['numAno'].astype(str) == str(ano))]
    itens = []
    for linha in frame.to_dict('records'):
        item = {
            'lote_id': lote, 'ano': ano, 'mes': int(linha['numMes']),
            'data_documento': pd.to_datetime(linha['datEmissao'], errors='coerce').date()
                if linha['datEmissao'] else None,
            'cargo': 'deputado_federal', 'fonte': 'Câmara dos Deputados - CEAP',
            'parlamentar_codigo': linha['ideCadastro'],
            'parlamentar_nome': linha['txNomeParlamentar'].strip(), 'partido': linha['sgPartido'],
            'categoria': linha['txtDescricao'].strip(), 'fornecedor_nome': linha['txtFornecedor'].strip(),
            'fornecedor_documento': linha['txtCNPJCPF'].strip(),
            'documento_numero': linha['txtNumero'].strip(),
            'valor_documento': decimal(linha['vlrDocumento']),
            'valor_glosa': decimal(linha['vlrGlosa']),
            'valor_reembolsado': decimal(linha['vlrLiquido']),
            'documento_url': linha['urlDocumento'].strip(),
        }
        item['chave_conteudo'] = chave(item)
        itens.append(item)
    cadastro = {
        (linha['ideCadastro'], linha['txNomeParlamentar'].strip(), linha['sgPartido'])
        for linha in frame.to_dict('records')
    }
    return itens, cadastro


def ler_senado(ano, lote, senadores):
    conteudo = requests.get(SENADO_CEAPS_URL.format(ano=ano), timeout=180).content
    frame = pd.read_csv(io.BytesIO(conteudo), sep=';', dtype=str, encoding='utf-8').fillna('')
    frame = frame[frame['NOME_SENADOR'].map(normalizar).isin(senadores)]
    itens = []
    for linha in frame.to_dict('records'):
        identificacao = senadores[normalizar(linha['NOME_SENADOR'])]
        item = {
            'lote_id': lote, 'ano': ano, 'mes': int(linha['MÊS']),
            'data_documento': pd.to_datetime(linha['DATA'], errors='coerce').date()
                if linha['DATA'] else None,
            'cargo': 'senador', 'fonte': 'Senado Federal - CEAPS',
            'parlamentar_codigo': linha['COD_SENADOR'],
            'parlamentar_nome': identificacao['NomeParlamentar'],
            'partido': identificacao.get('SiglaPartidoParlamentar'),
            'categoria': linha['TIPO_DESPESA'].strip(),
            'fornecedor_nome': linha['NOME_FORNECEDOR'].strip(),
            'fornecedor_documento': linha['CPF_CNPJ_FORNECEDOR'].strip(),
            'documento_numero': linha['DOCUMENTO'].strip(),
            'valor_documento': decimal(linha['VALOR_REEMBOLSADO']), 'valor_glosa': 0,
            'valor_reembolsado': decimal(linha['VALOR_REEMBOLSADO']), 'documento_url': None,
        }
        item['chave_conteudo'] = chave(item)
        itens.append(item)
    return itens


def obter_json(url, parametros=None):
    resposta = requests.get(url, params=parametros, timeout=90)
    resposta.raise_for_status()
    return resposta.json()


def ler_alego(ano, lote):
    periodos = obter_json(f'{ALEGO_API}/periodos')
    meses = next((item['meses'] for item in periodos if item['ano'] == ano), [])
    if not meses:
        raise ValueError(f'A Alego não publicou períodos para {ano}.')
    itens, cadastro = [], set()
    for mes in sorted(set(meses)):
        resumos = obter_json(f'{ALEGO_API}.json', {'ano': ano, 'mes': mes, 'todos': 'true'})
        for resumo in resumos:
            deputado = resumo['deputado']
            apresentado = decimal(resumo.get('valor_apresentado'))
            indenizado = decimal(resumo.get('valor_indenizado'))
            item = {
                'lote_id': lote, 'ano': ano, 'mes': mes, 'data_documento': None,
                'cargo': 'deputado_estadual',
                'fonte': 'Assembleia Legislativa de Goiás - Verba Indenizatória',
                'parlamentar_codigo': str(deputado['id']),
                'parlamentar_nome': deputado['nome'].strip(), 'partido': None,
                'categoria': 'TOTAL MENSAL (RESUMO OFICIAL)',
                'fornecedor_nome': None, 'fornecedor_documento': None,
                'documento_numero': str(resumo['id']),
                'valor_documento': apresentado,
                'valor_glosa': max(apresentado - indenizado, 0),
                'valor_reembolsado': indenizado,
                'documento_url': (
                    'https://transparencia.al.go.leg.br/gestao-parlamentar/'
                    f'verba-indenizatoria/exibir/{deputado["id"]}/{ano}/{mes}'
                ),
            }
            item['chave_conteudo'] = chave(item)
            itens.append(item)
            cadastro.add((str(deputado['id']), deputado['nome'].strip(), None))
    if not itens or len(cadastro) < 30:
        raise ValueError(
            f'Cobertura inesperada da Alego: {len(itens)} prestações e {len(cadastro)} deputados.'
        )
    return itens, cadastro


def carregar(ano):
    recursos = [CAMARA_URL.format(ano=ano), SENADO_CEAPS_URL.format(ano=ano),
                SENADORES_URL, f'{ALEGO_API}.json']
    with engine.begin() as conexao:
        lote = conexao.execute(text('''
            INSERT INTO lotes_despesas_parlamentares(ano,status,recursos)
            VALUES (:ano,'preparando',CAST(:recursos AS jsonb)) RETURNING id
        '''), {'ano': ano, 'recursos': json.dumps(recursos)}).scalar_one()
    try:
        senadores = obter_senadores_goias()
        itens_camara, deputados = ler_camara(ano, lote)
        itens_alego, deputados_estaduais = ler_alego(ano, lote)
        itens = itens_camara + ler_senado(ano, lote, senadores) + itens_alego
        colunas = list(itens[0])
        inserir = text(f'''INSERT INTO fatos_despesas_parlamentares({','.join(colunas)})
            VALUES({','.join(':' + coluna for coluna in colunas)}) ON CONFLICT DO NOTHING''')
        with engine.begin() as conexao:
            conexao.execute(text('''
                INSERT INTO parlamentares_lote
                  (lote_id,cargo,parlamentar_codigo,parlamentar_nome,partido)
                VALUES (:lote_id,:cargo,:codigo,:nome,:partido)
                ON CONFLICT DO NOTHING
            '''), [
                {'lote_id': lote, 'cargo': 'deputado_federal', 'codigo': codigo,
                 'nome': nome, 'partido': partido}
                for codigo, nome, partido in deputados
            ] + [
                {'lote_id': lote, 'cargo': 'senador',
                 'codigo': identificacao['CodigoParlamentar'],
                 'nome': identificacao['NomeParlamentar'],
                 'partido': identificacao.get('SiglaPartidoParlamentar')}
                for identificacao in senadores.values()
            ] + [
                {'lote_id': lote, 'cargo': 'deputado_estadual', 'codigo': codigo,
                 'nome': nome, 'partido': partido}
                for codigo, nome, partido in deputados_estaduais
            ])
            for inicio in range(0, len(itens), 1000):
                conexao.execute(inserir, itens[inicio:inicio + 1000])
            metricas = dict(conexao.execute(text('''
                SELECT COUNT(*) registros,
                  COUNT(DISTINCT cargo||':'||parlamentar_codigo) parlamentares_com_registros,
                  COUNT(*) FILTER (WHERE cargo='deputado_federal') registros_deputados,
                  COUNT(*) FILTER (WHERE cargo='senador') registros_senadores,
                  COUNT(*) FILTER (WHERE cargo='deputado_estadual') registros_deputados_estaduais,
                  SUM(valor_reembolsado) total_reembolsado
                FROM fatos_despesas_parlamentares WHERE lote_id=:lote
            '''), {'lote': lote}).mappings().one())
            metricas['parlamentares_cadastrados'] = conexao.execute(text('''
                SELECT COUNT(*) FROM parlamentares_lote WHERE lote_id=:lote
            '''), {'lote': lote}).scalar_one()
            if (metricas['registros_deputados'] == 0 or metricas['registros_senadores'] == 0
                    or metricas['registros_deputados_estaduais'] == 0):
                raise ValueError('Uma das fontes parlamentares não retornou registros.')
            conexao.execute(text('''
                UPDATE lotes_despesas_parlamentares SET status='arquivado'
                WHERE ano=:ano AND status='ativo'
            '''), {'ano': ano})
            conexao.execute(text('''
                UPDATE lotes_despesas_parlamentares
                SET status='ativo',finalizado_em=now(),metricas=CAST(:metricas AS jsonb)
                WHERE id=:lote
            '''), {'lote': lote, 'metricas': json.dumps(metricas, default=float)})
        return lote, metricas
    except Exception as erro:
        with engine.begin() as conexao:
            conexao.execute(text('''
                UPDATE lotes_despesas_parlamentares SET status='rejeitado',observacao=:erro
                WHERE id=:lote
            '''), {'lote': lote, 'erro': str(erro)})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ano', type=int, required=True)
    argumentos = parser.parse_args()
    print(carregar(argumentos.ano))
