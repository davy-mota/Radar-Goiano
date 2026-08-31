import argparse
import concurrent.futures
import re
import time
import unicodedata
from datetime import date

import requests
from sqlalchemy import text

from database import engine

LOCALIDADES_URL = 'https://servicodados.ibge.gov.br/api/v1/localidades/estados/52/municipios'
POPULACAO_URL = (
    'https://servicodados.ibge.gov.br/api/v1/pesquisas/-/periodos/'
    '{ano}/indicadores/29171/resultados/{codigo}?groupBy=localidade'
)
FONTE = 'IBGE - Estimativas da População'
ALIASES_MANUAIS = {'BOM JESUS': 5203500}


def normalizar_nome(valor):
    sem_acentos = ''.join(
        caractere for caractere in unicodedata.normalize('NFKD', valor)
        if not unicodedata.combining(caractere)
    )
    return re.sub(r'\s+', ' ', re.sub(r'[^A-Z0-9]+', ' ', sem_acentos.upper())).strip()


def obter_json(url, tentativas=4):
    for tentativa in range(tentativas):
        try:
            resposta = requests.get(url, timeout=60)
            resposta.raise_for_status()
            return resposta.json()
        except requests.RequestException:
            if tentativa == tentativas - 1:
                raise
            time.sleep(2 ** tentativa)


def obter_populacao(municipio, ano):
    codigo = municipio['id']
    resultado = obter_json(POPULACAO_URL.format(ano=ano, codigo=codigo))
    if not resultado:
        raise ValueError(f'IBGE não retornou população para {codigo}.')
    valor = resultado[0]['res'][0]['res'].get(str(ano))
    if not valor or not str(valor).isdigit():
        raise ValueError(f'População inválida para {codigo}: {valor!r}')
    return codigo, int(valor)


def carregar(ano):
    municipios = obter_json(LOCALIDADES_URL)
    if len(municipios) != 246:
        raise ValueError(f'Esperados 246 municípios de Goiás; recebidos {len(municipios)}.')

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        populacoes = dict(executor.map(lambda item: obter_populacao(item, ano), municipios))

    fonte_url = POPULACAO_URL.format(ano=ano, codigo='{codigo}')
    referencia = date(ano, 7, 1)
    with engine.begin() as conexao:
        conexao.execute(text("SET LOCAL lock_timeout = '10s'"))
        for municipio in municipios:
            regiao_imediata = municipio.get('regiao-imediata') or {}
            regiao_intermediaria = regiao_imediata.get('regiao-intermediaria') or {}
            conexao.execute(text('''
                INSERT INTO municipios_ibge
                    (codigo_ibge, nome, uf, regiao_imediata, regiao_intermediaria, atualizado_em)
                VALUES (:codigo, :nome, 'GO', :imediata, :intermediaria, now())
                ON CONFLICT (codigo_ibge) DO UPDATE SET
                    nome = EXCLUDED.nome,
                    regiao_imediata = EXCLUDED.regiao_imediata,
                    regiao_intermediaria = EXCLUDED.regiao_intermediaria,
                    atualizado_em = now()
            '''), {
                'codigo': municipio['id'],
                'nome': municipio['nome'],
                'imediata': regiao_imediata.get('nome'),
                'intermediaria': regiao_intermediaria.get('nome'),
            })
            conexao.execute(text('''
                INSERT INTO populacoes_municipais
                    (codigo_ibge, ano, populacao, referencia, fonte_url)
                VALUES (:codigo, :ano, :populacao, :referencia, :fonte)
                ON CONFLICT (codigo_ibge, ano) DO UPDATE SET
                    populacao = EXCLUDED.populacao,
                    referencia = EXCLUDED.referencia,
                    fonte_url = EXCLUDED.fonte_url,
                    carregado_em = now()
            '''), {
                'codigo': municipio['id'], 'ano': ano,
                'populacao': populacoes[municipio['id']],
                'referencia': referencia, 'fonte': fonte_url,
            })

        nomes_ibge = {}
        for municipio in municipios:
            nomes_ibge.setdefault(normalizar_nome(municipio['nome']), []).append(municipio['id'])
        nomes_origem = conexao.execute(text('''
            SELECT DISTINCT municipio
            FROM vw_repasses_municipais_ativos
            ORDER BY municipio
        ''')).scalars().all()
        for nome in nomes_origem:
            normalizado = normalizar_nome(nome)
            candidatos = nomes_ibge.get(normalizado, [])
            codigo = candidatos[0] if len(candidatos) == 1 else None
            metodo = 'exato_normalizado' if codigo else 'pendente'
            conexao.execute(text('''
                INSERT INTO aliases_municipios
                    (fonte, nome_origem, nome_normalizado, codigo_ibge, metodo, revisado_em)
                VALUES ('repasses_goias', :nome, :normalizado, :codigo, :metodo,
                        CASE WHEN :codigo IS NOT NULL THEN now() END)
                ON CONFLICT (fonte, nome_origem) DO UPDATE SET
                    nome_normalizado = EXCLUDED.nome_normalizado,
                    codigo_ibge = CASE
                        WHEN aliases_municipios.metodo = 'manual' THEN aliases_municipios.codigo_ibge
                        ELSE EXCLUDED.codigo_ibge
                    END,
                    metodo = CASE
                        WHEN aliases_municipios.metodo = 'manual' THEN aliases_municipios.metodo
                        ELSE EXCLUDED.metodo
                    END,
                    revisado_em = CASE
                        WHEN aliases_municipios.metodo = 'manual' THEN aliases_municipios.revisado_em
                        ELSE EXCLUDED.revisado_em
                    END
            '''), {'nome': nome, 'normalizado': normalizado, 'codigo': codigo, 'metodo': metodo})

        for nome_origem, codigo_ibge in ALIASES_MANUAIS.items():
            municipio_oficial = conexao.execute(text('''
                SELECT nome FROM municipios_ibge WHERE codigo_ibge = :codigo
            '''), {'codigo': codigo_ibge}).scalar_one_or_none()
            if municipio_oficial is None:
                raise ValueError(f'Alias manual aponta para código IBGE inexistente: {codigo_ibge}.')
            conexao.execute(text('''
                UPDATE aliases_municipios SET
                    codigo_ibge = :codigo,
                    metodo = 'manual',
                    revisado_em = now(),
                    observacao = :observacao
                WHERE fonte = 'repasses_goias' AND nome_origem = :nome
            '''), {
                'codigo': codigo_ibge,
                'nome': nome_origem,
                'observacao': f'Conciliação explícita com {municipio_oficial}.',
            })

        metricas = conexao.execute(text('''
            SELECT
                COUNT(*) AS aliases,
                COUNT(codigo_ibge) AS conciliados,
                COUNT(*) FILTER (WHERE codigo_ibge IS NULL) AS pendentes
            FROM aliases_municipios WHERE fonte = 'repasses_goias'
        ''')).mappings().one()
    return dict(metricas)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ano', type=int, required=True)
    argumentos = parser.parse_args()
    print(carregar(argumentos.ano))
