import argparse
import hashlib
import io
import json

import pandas as pd
import requests
from sqlalchemy import text

from carga_populacao_ibge import normalizar_nome
from database import engine

URL_CSV = 'https://www.senado.leg.br/transparencia/LAI/verba/despesa_ceaps_{ano}.csv'
URL_SENADORES_GO = 'https://legis.senado.leg.br/dadosabertos/senador/lista/atual?uf=GO'

CAMPOS = {
    'tipo_despesa': 'TIPO_DESPESA',
    'cnpj_cpf': 'CNPJ_CPF',
    'fornecedor': 'FORNECEDOR',
    'documento': 'DOCUMENTO',
    'detalhamento': 'DETALHAMENTO',
    'cod_documento': 'COD_DOCUMENTO',
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


def obter_senadores_go():
    """Nomes de titulares e suplentes que já ocuparam uma das três vagas de Goiás no
    Senado. O CEAPS só publica o nome do senador, sem UF nem partido nem um
    identificador estável, então a associação a Goiás é feita por nome normalizado —
    a mesma limitação de identidade já registrada para outras fontes deste projeto."""
    resposta = requests.get(URL_SENADORES_GO, headers={'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0'}, timeout=60)
    resposta.raise_for_status()
    parlamentares = resposta.json()['ListaParlamentarEmExercicio']['Parlamentares']['Parlamentar']
    if isinstance(parlamentares, dict):
        parlamentares = [parlamentares]

    pessoas = {}
    for parlamentar in parlamentares:
        identificacao = parlamentar['IdentificacaoParlamentar']
        partido = identificacao.get('SiglaPartidoParlamentar')
        pessoas[normalizar_nome(identificacao['NomeParlamentar'])] = {
            'nome': identificacao['NomeParlamentar'], 'partido': partido, 'papel': 'titular',
        }
        suplentes = parlamentar.get('Mandato', {}).get('Suplentes', {}).get('Suplente', [])
        if isinstance(suplentes, dict):
            suplentes = [suplentes]
        for suplente in suplentes:
            nome_suplente = suplente.get('NomeParlamentar')
            if nome_suplente:
                pessoas.setdefault(normalizar_nome(nome_suplente), {
                    'nome': nome_suplente, 'partido': partido, 'papel': 'suplente',
                })
    return pessoas


def carregar(ano):
    senadores_go = obter_senadores_go()
    url = URL_CSV.format(ano=ano)
    conteudo = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=180).content
    frame = pd.read_csv(
        io.BytesIO(conteudo), sep=';', dtype=str, encoding='ISO-8859-1', skiprows=1, quotechar='"',
    ).fillna('')

    obrigatorios = {'ANO', 'MES', 'SENADOR', 'DATA', 'VALOR_REEMBOLSADO', *CAMPOS.values()}
    ausentes = obrigatorios.difference(frame.columns)
    if ausentes:
        raise ValueError(f'Colunas obrigatórias ausentes: {sorted(ausentes)}')

    registros_fonte = len(frame)
    frame['_normalizado'] = frame['SENADOR'].apply(normalizar_nome)
    frame = frame[frame['_normalizado'].isin(senadores_go)].copy()
    registros_descartados = registros_fonte - len(frame)
    if frame.empty:
        raise ValueError(f'Nenhum registro de senador de Goiás encontrado para {ano}.')

    recurso_meta = {'url': url, 'formato': 'csv', 'senadores_considerados': sorted({p['nome'] for p in senadores_go.values()})}
    with engine.begin() as conexao:
        lote = conexao.execute(text('''
            INSERT INTO lotes_senadores(status, ano, recurso)
            VALUES ('preparando', :ano, CAST(:recurso AS jsonb)) RETURNING id
        '''), {'ano': ano, 'recurso': json.dumps(recurso_meta, ensure_ascii=False)}).scalar_one()

    try:
        itens = []
        for linha in frame.to_dict('records'):
            pessoa = senadores_go[linha['_normalizado']]
            item = {
                'lote_id': lote, 'ano': ano, 'mes': int(linha['MES']) if linha['MES'] else None,
                'nome_senador': pessoa['nome'], 'partido': pessoa['partido'], 'papel': pessoa['papel'],
            }
            item.update({destino: str(linha[origem]).strip() for destino, origem in CAMPOS.items()})
            item['valor_reembolsado'] = valor_decimal(linha['VALOR_REEMBOLSADO'])
            item['data_documento'] = (
                pd.to_datetime(linha['DATA'], format='mixed', dayfirst=True).date()
                if linha.get('DATA') else None
            )
            item['chave_conteudo'] = hashlib.sha256(
                json.dumps(item, sort_keys=True, default=str, ensure_ascii=False).encode('utf-8')
            ).hexdigest()
            itens.append(item)

        colunas = list(itens[0])
        inserir = text(f'''INSERT INTO fatos_despesas_senadores({",".join(colunas)})
            VALUES({",".join(":" + coluna for coluna in colunas)}) ON CONFLICT DO NOTHING''')
        with engine.begin() as conexao:
            for inicio in range(0, len(itens), 1000):
                conexao.execute(inserir, itens[inicio:inicio + 1000])

            metricas = dict(conexao.execute(text('''
                SELECT COUNT(*) registros, COUNT(DISTINCT nome_senador) senadores,
                       SUM(valor_reembolsado) reembolsado
                FROM fatos_despesas_senadores WHERE lote_id = :lote
            '''), {'lote': lote}).mappings().one())
            metricas['registros_fonte'] = registros_fonte
            metricas['registros_descartados_fora_go'] = registros_descartados
            if not metricas['registros'] or not metricas['reembolsado']:
                raise ValueError('Carga sem registros ou sem valor reembolsado.')

            conexao.execute(text('''
                UPDATE lotes_senadores SET status = 'arquivado'
                WHERE status = 'ativo' AND ano = :ano
            '''), {'ano': ano})
            conexao.execute(text('''
                UPDATE lotes_senadores SET status = 'ativo', finalizado_em = now(), metricas = CAST(:m AS jsonb)
                WHERE id = :lote
            '''), {'lote': lote, 'm': json.dumps(metricas, default=float)})
        return lote, metricas
    except Exception as erro:
        with engine.begin() as conexao:
            conexao.execute(text('''
                UPDATE lotes_senadores SET status = 'rejeitado', observacao = :erro WHERE id = :lote
            '''), {'lote': lote, 'erro': str(erro)})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Carrega despesas (CEAPS) dos senadores de Goiás.')
    parser.add_argument('--ano', type=int, required=True)
    argumentos = parser.parse_args()
    print(carregar(argumentos.ano))
