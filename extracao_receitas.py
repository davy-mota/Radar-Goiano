import requests
import pandas as pd
from sqlalchemy import create_engine
from urllib.parse import quote_plus
import zipfile
import os
import re

# =====================================================================
# 1. CONFIGURAÇÕES
# =====================================================================
senha_segura = quote_plus("gatodebotas") # <-- COLOQUE SUA SENHA AQUI
engine = create_engine(f'postgresql://postgres:{senha_segura}@localhost:5432/gastos_governamentais') # <-- SEU BANCO

colunas_banco = [
    "ano_exercicio", "mes_exercicio", "nome_orgao", "categoria_receita", 
    "origem_receita", "valor_previsto", "valor_arrecadado", "data_arrecadacao"
]

# =====================================================================
# 2. SELECIONANDO OS ALVOS (RECEITAS)
# =====================================================================
print("🔍 Buscando links da base de RECEITAS no portal de Goiás...")

# 🔥 CORREÇÃO 1: O ID oficial no portal mudou para "receitas-detalhadas"
url_catalogo = "https://dadosabertos.go.gov.br/api/3/action/package_show?id=receitas-detalhadas"

# 🔥 CORREÇÃO 2: Blindagem para não dar erro se a API falhar
resposta = requests.get(url_catalogo)
if resposta.status_code != 200:
    print(f"Erro na API do portal. Status: {resposta.status_code}")
recursos = resposta.json().get('result', {}).get('resources', [])

arquivos_alvo = []
for r in recursos:
    nome = r.get('name', '')
    formato = r.get('format', '').upper()
    if '2025' in nome and formato == 'CSV':
        arquivos_alvo.append({'nome': nome, 'url': r['url'], 'tipo': 'CSV'})
    elif '2006' in nome or '2024' in nome or '-' in nome and formato == 'ZIP':
        arquivos_alvo.append({'nome': nome, 'url': r['url'], 'tipo': 'ZIP'})

# =====================================================================
# 3. FUNÇÃO DE LIMPEZA E MAPEAMENTO (CAÇADOR DE RECEITAS)
# =====================================================================
def transformar_e_salvar(df_lote, ano_do_arquivo):
    df_lote.columns = df_lote.columns.str.strip().str.upper()
    
    # 3.1 CAÇADOR DE DATAS E ANOS
    col_data = next((col for col in ['DATAARRECADACAO', 'DATA_ARRECADACAO', 'DATA', 'DATALANCAMENTO'] if col in df_lote.columns), None)
    col_ano = next((col for col in ['EXERCICIO', 'ANO_EXERCICIO', 'ANO'] if col in df_lote.columns), None)

    if col_data:
        datas_limpas = df_lote[col_data].astype(str).str[:10]
        datas = pd.to_datetime(datas_limpas, errors='coerce')
        df_lote['ano_exercicio'] = datas.dt.year.fillna(0).astype(int)
        df_lote['mes_exercicio'] = datas.dt.month.fillna(0).astype(int)
        df_lote['data_arrecadacao'] = datas.dt.strftime('%Y-%m-%d').where(datas.notna(), None)
    elif col_ano:
        df_lote['ano_exercicio'] = pd.to_numeric(df_lote[col_ano], errors='coerce').fillna(0).astype(int)
        df_lote['mes_exercicio'] = 0
        df_lote['data_arrecadacao'] = None
    else:
        df_lote['ano_exercicio'], df_lote['mes_exercicio'], df_lote['data_arrecadacao'] = 0, 0, None

    if ano_do_arquivo > 0:
        df_lote.loc[df_lote['ano_exercicio'] == 0, 'ano_exercicio'] = ano_do_arquivo

    # 3.2 MAPEAMENTO DAS COLUNAS TEXTUAIS
    df_lote['nome_orgao'] = df_lote.get('NOMEORGAO', df_lote.get('ORGAO', 'NÃO INFORMADO'))
    df_lote['categoria_receita'] = df_lote.get('CATEGORIA', df_lote.get('CATEGORIAECONOMICA', 'NÃO INFORMADA'))
    df_lote['origem_receita'] = df_lote.get('ORIGEM', df_lote.get('ORIGEMRECEITA', 'NÃO INFORMADA'))

    # 3.3 CAÇADOR DE VALORES MONETÁRIOS (Atualizado)
    col_previsto = next((col for col in ['VALORPREVISTO', 'PREVISAO', 'PREVISTO'] if col in df_lote.columns), None)
    col_arrecadado = next((col for col in ['RECEITAREALIZADA', 'VALORARRECADADO', 'ARRECADADO', 'REALIZADO', 'VALOR'] if col in df_lote.columns), None)

    for nova_col, col_antiga in [('valor_previsto', col_previsto), ('valor_arrecadado', col_arrecadado)]:
        if col_antiga:
            df_lote[nova_col] = df_lote[col_antiga].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df_lote[nova_col] = pd.to_numeric(df_lote[nova_col], errors='coerce').fillna(0)
        else:
            df_lote[nova_col] = 0

    # 3.4 FILTRAGEM FINAL PARA O BANCO
    for col in colunas_banco:
        if col not in df_lote.columns: df_lote[col] = None
    df_lote = df_lote[colunas_banco]
            
    df_lote.to_sql('receitas_estaduais', engine, if_exists='append', index=False)
    return len(df_lote)

# =====================================================================
# 4. MOTOR DE EXTRAÇÃO
# =====================================================================
total_geral = 0
tamanho_chunk = 100000

def descobrir_ano_no_nome(texto):
    match = re.search(r'(20\d{2})', texto)
    return int(match.group(1)) if match else 0

for arq in arquivos_alvo:
    print(f"\n🚀 Iniciando Extração: {arq['nome']} ...")
    try:
        if arq['tipo'] == 'CSV':
            ano_arquivo = descobrir_ano_no_nome(arq['nome'])
            df_temp = pd.read_csv(arq['url'], sep=';', encoding='latin1', dtype=str, on_bad_lines='skip')
            linhas_salvas = transformar_e_salvar(df_temp, ano_arquivo)
            total_geral += linhas_salvas
            print(f"  ✅ Salvo! (Ano: {ano_arquivo}) | +{linhas_salvas} receitas registradas.")

        elif arq['tipo'] == 'ZIP':
            print("  ⏳ Baixando o arquivo ZIP Histórico...")
            resposta_zip = requests.get(arq['url'], stream=True)
            with open("temp_receitas.zip", "wb") as f:
                for pedaço in resposta_zip.iter_content(chunk_size=8192):
                    f.write(pedaço)
            
            with zipfile.ZipFile("temp_receitas.zip", "r") as z:
                csvs_internos = [n for n in z.namelist() if n.upper().endswith('.CSV') and '__MACOSX' not in n.upper() and not n.split('/')[-1].startswith('._')]
                
                for nome_csv in csvs_internos:
                    ano_arquivo = descobrir_ano_no_nome(nome_csv)
                    print(f"    ➡️ Lendo: {nome_csv} (Ano: {ano_arquivo})")
                    
                    with z.open(nome_csv) as f_csv:
                        for chunk in pd.read_csv(f_csv, sep=';', encoding='latin1', dtype=str, on_bad_lines='skip', chunksize=tamanho_chunk):
                            linhas_salvas = transformar_e_salvar(chunk, ano_arquivo)
                            total_geral += linhas_salvas
                            print(f"      Lote processado. Acumulado: {total_geral}")
                            
            if os.path.exists("temp_receitas.zip"): os.remove("temp_receitas.zip")

    except Exception as e:
        print(f"  ❌ Erro no arquivo {arq['nome']}: {e}")

print(f"\n🎉 NOVO BANCO PRONTO! Total de {total_geral} receitas salvas na tabela 'receitas_estaduais'.")