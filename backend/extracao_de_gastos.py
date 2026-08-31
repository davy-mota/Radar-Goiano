import requests
import pandas as pd
from database import engine
import zipfile
import os
import re

# =====================================================================
# 1. CONFIGURAÇÕES
# =====================================================================
colunas_banco = [
    "numero_empenho", "ano_exercicio", "mes_exercicio", "codigo_orgao", 
    "nome_orgao", "cnpj_cpf_credor", "nome_credor", "data_emissao", 
    "funcao", "subfuncao", "natureza_despesa", "fonte_recurso", 
    "valor_empenhado", "valor_liquidado", "valor_pago"
]

# =====================================================================
# 2. SELECIONANDO OS ALVOS (PAGAMENTOS)
# =====================================================================
print("🔍 Buscando links da base de PAGAMENTOS no portal de Goiás...")
url_catalogo = "https://dadosabertos.go.gov.br/api/3/action/package_show?id=pagamentos"
recursos = requests.get(url_catalogo).json().get('result', {}).get('resources', [])

arquivos_alvo = []
for r in recursos:
    nome = r.get('name', '')
    formato = r.get('format', '').upper()
    if '2025' in nome and formato == 'CSV':
        arquivos_alvo.append({'nome': nome, 'url': r['url'], 'tipo': 'CSV'})
    elif '2003 - 2024' in nome and formato == 'ZIP':
        arquivos_alvo.append({'nome': nome, 'url': r['url'], 'tipo': 'ZIP'})

# =====================================================================
# 3. FUNÇÃO DE LIMPEZA E MAPEAMENTO (TANQUE DE GUERRA)
# =====================================================================
def transformar_e_salvar(df_lote, ano_do_arquivo):
    df_lote.columns = df_lote.columns.str.strip().str.upper()
    
    def extrai_doc(col):
        if col in df_lote.columns:
            return df_lote[col].astype(str).str.replace(r'\.0$', '', regex=True).str.replace(r'(?i)^nan$', '', regex=True).str.strip()
        return ''
        
    col_cpf = next((col for col in ['CPFCREDOR', 'CPFCREDC', 'CPF'] if col in df_lote.columns), '')
    col_cnpj = next((col for col in ['CNPJCREDOR', 'CNPJ'] if col in df_lote.columns), '')
    df_lote['cnpj_cpf_credor'] = extrai_doc(col_cnpj) + extrai_doc(col_cpf)
    
    # CAÇADOR DE DATAS: Pega a primeira que achar
    col_data = next((col for col in ['DATAPAGAMENTO', 'DATA_PAGAMENTO', 'DATAEMISSÃO', 'DATAEMISSAO', 'DATA'] if col in df_lote.columns), None)
    col_ano = next((col for col in ['EXERCICIO', 'ANO_EXERCICIO', 'ANO'] if col in df_lote.columns), None)

    if col_data:
        # Pega apenas os 10 primeiros caracteres (YYYY-MM-DD) para ignorar o fuso horário maluco
        datas_limpas = df_lote[col_data].astype(str).str[:10]
        datas = pd.to_datetime(datas_limpas, errors='coerce')
        
        df_lote['ano_exercicio'] = datas.dt.year.fillna(0).astype(int)
        df_lote['mes_exercicio'] = datas.dt.month.fillna(0).astype(int)
        df_lote['data_emissao'] = datas.dt.strftime('%Y-%m-%d').where(datas.notna(), None)
    elif col_ano:
        df_lote['ano_exercicio'] = pd.to_numeric(df_lote[col_ano], errors='coerce').fillna(0).astype(int)
        df_lote['mes_exercicio'] = 0
        df_lote['data_emissao'] = None
    else:
        df_lote['ano_exercicio'], df_lote['mes_exercicio'], df_lote['data_emissao'] = 0, 0, None

    if ano_do_arquivo > 0:
        df_lote.loc[df_lote['ano_exercicio'] == 0, 'ano_exercicio'] = ano_do_arquivo

    # MAPEAMENTO: Procura as colunas essenciais
    df_lote['numero_empenho'] = df_lote.get('NUMNOTAEMPENHO', df_lote.get('EMPENHO', None))
    df_lote['codigo_orgao'] = df_lote.get('CODORGAO', None)
    df_lote['nome_orgao'] = df_lote.get('NOMEORGAO', None)
    df_lote['nome_credor'] = df_lote.get('NOMECREDOR', None)
    df_lote['funcao'] = df_lote.get('NOMEFUNCAO', df_lote.get('FUNCAO', None))
    
    # CAÇADOR DE VALOR: Mesmo se eles chamarem de EMPENHADO no arquivo de Pagamentos, nós puxamos!
    col_valor = next((col for col in ['VALORPAGAMENTO', 'VALORPAGO', 'VALOREMPENHADO', 'VALOR'] if col in df_lote.columns), None)
    if col_valor:
        df_lote['valor_pago'] = df_lote[col_valor].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df_lote['valor_pago'] = pd.to_numeric(df_lote['valor_pago'], errors='coerce').fillna(0)
    else:
        df_lote['valor_pago'] = 0

    df_lote['valor_empenhado'] = 0
    df_lote['valor_liquidado'] = 0
    
    for col in colunas_banco:
        if col not in df_lote.columns: df_lote[col] = None
    df_lote = df_lote[colunas_banco]
            
    df_lote.to_sql('pagamentos_estaduais', engine, if_exists='append', index=False)
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
            print(f"  ✅ Salvo! (Ano: {ano_arquivo}) | +{linhas_salvas} registros.")

        elif arq['tipo'] == 'ZIP':
            print("  ⏳ Baixando o arquivo ZIP Histórico...")
            resposta_zip = requests.get(arq['url'], stream=True)
            with open("temp_pagamentos.zip", "wb") as f:
                for pedaço in resposta_zip.iter_content(chunk_size=8192):
                    f.write(pedaço)
            
            with zipfile.ZipFile("temp_pagamentos.zip", "r") as z:
                # 🔥 O FILTRO DE FANTASMAS: Ignora os arquivos lixo do MacOS
                csvs_internos = [n for n in z.namelist() if n.upper().endswith('.CSV') and '__MACOSX' not in n.upper() and not n.split('/')[-1].startswith('._')]
                
                for nome_csv in csvs_internos:
                    ano_arquivo = descobrir_ano_no_nome(nome_csv)
                    print(f"    ➡️ Lendo: {nome_csv} (Ano: {ano_arquivo})")
                    
                    with z.open(nome_csv) as f_csv:
                        for chunk in pd.read_csv(f_csv, sep=';', encoding='latin1', dtype=str, on_bad_lines='skip', chunksize=tamanho_chunk):
                            linhas_salvas = transformar_e_salvar(chunk, ano_arquivo)
                            total_geral += linhas_salvas
                            print(f"      Lote processado. Acumulado: {total_geral}")
                            
            if os.path.exists("temp_pagamentos.zip"): os.remove("temp_pagamentos.zip")

    except Exception as e:
        print(f"  ❌ Erro no arquivo {arq['nome']}: {e}")

print(f"\n🎉 NOVO BANCO PRONTO! Total de {total_geral} pagamentos salvos na tabela 'pagamentos_estaduais'.")
