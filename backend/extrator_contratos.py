import requests
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import zipfile
import os
import re
import sys

# =====================================================================
# 1. CONFIGURAÇÕES E LIMPEZA INICIAL
# =====================================================================
senha_segura = quote_plus("gatodebotas") # <-- SUA SENHA
engine = create_engine(f'postgresql://postgres:{senha_segura}@localhost:5432/gastos_governamentais') 

colunas_banco = [
    "ano_exercicio", "nome_orgao", "numero_contrato", "cnpj_cpf_contratado", 
    "nome_contratado", "objeto_contrato", "modalidade_licitacao", 
    "valor_contrato", "data_assinatura"
]

print("🧹 Limpando dados antigos do banco para a nova extração...")
with engine.connect() as conexao:
    conexao.execute(text("TRUNCATE TABLE contratos_licitacoes;"))
    conexao.commit()

# =====================================================================
# 2. SELECIONANDO OS ALVOS (COM FILTRO ANTI-DUPLICAÇÃO)
# =====================================================================
print("🔍 Pesquisando ficheiros na API...")

url_busca = "https://dadosabertos.go.gov.br/api/3/action/package_search?q=contrato"

try:
    resposta = requests.get(url_busca)
    if resposta.status_code != 200: sys.exit() 
        
    dados_json = resposta.json()
    recursos = []
    for pacote in dados_json.get('result', {}).get('results', []):
        recursos.extend(pacote.get('resources', []))
        
except Exception as e:
    print(f"❌ Erro de ligação: {e}")
    sys.exit()

arquivos_alvo = []
for r in recursos:
    nome = r.get('name', '').upper()
    formato = r.get('format', '').upper()
    
    # 🔥 O FILTRO INTELIGENTE: Ignora arquivos que são a junção de tudo
    if 'CONSOLIDADO' in nome or 'GERAL' in nome or 'TODOS' in nome or 'COMPLETO' in nome:
        print(f"   -> 🛑 Ignorando arquivo consolidado para evitar duplicidade: {nome}")
        continue
    
    if '2025' in nome and formato == 'CSV':
        arquivos_alvo.append({'nome': nome, 'url': r['url'], 'tipo': 'CSV'})
    elif ('2003' in nome or '2024' in nome or '-' in nome) and formato == 'ZIP':
        arquivos_alvo.append({'nome': nome, 'url': r['url'], 'tipo': 'ZIP'})

if not arquivos_alvo:
    print("⚠️ Não foram encontrados ficheiros compatíveis.")
    sys.exit()

print(f"✅ Encontrados {len(arquivos_alvo)} ficheiros individuais para descarregar.")

# =====================================================================
# 3. FUNÇÃO DE LIMPEZA E MAPEAMENTO (DIRETO PARA O BANCO)
# =====================================================================
def transformar_e_salvar(df_lote, ano_do_arquivo):
    colunas_originais = df_lote.columns
    colunas_limpas = colunas_originais.str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.upper()
    mapa_colunas = dict(zip(colunas_limpas, colunas_originais))
    
    def achar_coluna(possibilidades):
        for p in possibilidades:
            if p in mapa_colunas: return mapa_colunas[p]
        return None

    # Datas e Anos
    col_data = achar_coluna(['DATAASSINATURA', 'DATACONTRATO', 'INICIOVIGENCIA', 'DATA', 'DATAPUBLICACAO'])
    col_ano = achar_coluna(['EXERCICIO', 'ANOEXERCICIO', 'ANOCONTRATO', 'ANO'])

    if col_data:
        datas_limpas = df_lote[col_data].astype(str).str[:10]
        datas = pd.to_datetime(datas_limpas, errors='coerce')
        df_lote['ano_exercicio'] = datas.dt.year.fillna(0).astype(int)
        df_lote['data_assinatura'] = datas.dt.strftime('%Y-%m-%d').where(datas.notna(), None)
    elif col_ano:
        df_lote['ano_exercicio'] = pd.to_numeric(df_lote[col_ano], errors='coerce').fillna(0).astype(int)
        df_lote['data_assinatura'] = None
    else:
        df_lote['ano_exercicio'], df_lote['data_assinatura'] = 0, None

    if ano_do_arquivo > 0:
        df_lote.loc[df_lote['ano_exercicio'] == 0, 'ano_exercicio'] = ano_do_arquivo

    # Textos
    col_orgao = achar_coluna(['NOMEORGAO', 'ORGAO'])
    col_num_contrato = achar_coluna(['NUMEROCONTRATO', 'CONTRATO', 'NUMERO'])
    col_nome_contratado = achar_coluna(['RAZAOSOCIALCONTRATADO', 'NOMECONTRATADO', 'FORNECEDOR', 'CONTRATADO', 'CREDOR'])
    col_objeto = achar_coluna(['OBJETOAQUISICAO', 'OBJETOCONTRATO', 'OBJETO', 'DESCRICAO'])
    col_modalidade = achar_coluna(['TIPOAQUISICAO', 'MODALIDADELICITACAO', 'MODALIDADE', 'TIPOLICITACAO'])
    
    df_lote['nome_orgao'] = df_lote[col_orgao] if col_orgao else 'NÃO INFORMADO'
    df_lote['numero_contrato'] = df_lote[col_num_contrato] if col_num_contrato else 'S/N'
    df_lote['nome_contratado'] = df_lote[col_nome_contratado] if col_nome_contratado else 'NÃO INFORMADO'
    df_lote['objeto_contrato'] = df_lote[col_objeto] if col_objeto else 'NÃO INFORMADO'
    df_lote['modalidade_licitacao'] = df_lote[col_modalidade] if col_modalidade else 'NÃO INFORMADA'
    
    # Documentos
    col_cnpj = achar_coluna(['CNPJCONTRATADO', 'CNPJCONTRATANTE', 'CNPJ'])
    col_cpf = achar_coluna(['CPFCONTRATADO', 'CPFCONTRATANTE', 'CPF', 'DOCUMENTO'])
    
    def limpa_doc_series(serie):
        if serie is None: return ''
        s = serie.astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        s = s.replace({'-1000000000': '', 'nan': '', 'None': ''})
        return s
        
    df_lote['cnpj_cpf_contratado'] = limpa_doc_series(df_lote[col_cnpj] if col_cnpj else None) + limpa_doc_series(df_lote[col_cpf] if col_cpf else None)
    df_lote.loc[df_lote['cnpj_cpf_contratado'] == '', 'cnpj_cpf_contratado'] = None

    # Valores Monerários
    col_valor = achar_coluna(['VALORAQUISICAO', 'VALORCONTRATO', 'VALORTOTAL', 'VALORGLOBAL', 'VALOR'])
    
    if col_valor:
        def converter_para_numero(val_bruto):
            val_str = str(val_bruto).strip().replace('"', '').replace("'", "").replace('R$', '').replace(' ', '')
            if val_str.lower() in ['nan', 'none', '']: return 0.0
            if ',' in val_str: val_str = val_str.replace('.', '').replace(',', '.')
            elif val_str.count('.') > 1: val_str = val_str.replace('.', '')
            try:
                valor_float = float(val_str)
                if valor_float > 1000000000:
                    print(f"      ⚠️ ALERTA: Valor absurdo detectado ({valor_float}). Inserido no banco para correção manual.")
                return valor_float
            except: return 0.0

        df_lote['valor_contrato'] = df_lote[col_valor].apply(converter_para_numero)
    else:
        df_lote['valor_contrato'] = 0.0

    # Gravação no Banco
    for col in colunas_banco:
        if col not in df_lote.columns: df_lote[col] = None
    
    df_lote_db = df_lote[colunas_banco]
    df_lote_db.to_sql('contratos_licitacoes', engine, if_exists='append', index=False)
    return len(df_lote_db)

# =====================================================================
# 4. MOTOR DE EXTRAÇÃO
# =====================================================================
total_geral = 0
tamanho_chunk = 100000

def descobrir_ano_no_nome(texto):
    match = re.search(r'(20\d{2})', texto)
    return int(match.group(1)) if match else 0

for arq in arquivos_alvo:
    print(f"\n🚀 A Iniciar Extração: {arq['nome']} ...")
    try:
        if arq['tipo'] == 'CSV':
            ano_arquivo = descobrir_ano_no_nome(arq['nome'])
            resposta_csv = requests.get(arq['url'])
            with open("temp_arquivo.csv", "wb") as f: f.write(resposta_csv.content)
            
            with open("temp_arquivo.csv", "r", encoding='latin1') as f:
                separador = ';' if ';' in f.readline() else ','
                
            df_temp = pd.read_csv("temp_arquivo.csv", sep=separador, encoding='latin1', dtype=str, on_bad_lines='skip')
            linhas_salvas = transformar_e_salvar(df_temp, ano_arquivo)
            total_geral += linhas_salvas
            os.remove("temp_arquivo.csv")
            print(f"  ✅ +{linhas_salvas} contratos registados.")

        elif arq['tipo'] == 'ZIP':
            resposta_zip = requests.get(arq['url'], stream=True)
            with open("temp_contratos.zip", "wb") as f:
                for pedaço in resposta_zip.iter_content(chunk_size=8192): f.write(pedaço)
            
            with zipfile.ZipFile("temp_contratos.zip", "r") as z:
                csvs = [n for n in z.namelist() if n.upper().endswith('.CSV') and '__MACOSX' not in n.upper()]
                for nome_csv in csvs:
                    ano_arquivo = descobrir_ano_no_nome(nome_csv)
                    with z.open(nome_csv) as f_csv:
                        separador = ';' if ';' in f_csv.readline().decode('latin1', errors='ignore') else ','
                        f_csv.seek(0)
                        for chunk in pd.read_csv(f_csv, sep=separador, encoding='latin1', dtype=str, on_bad_lines='skip', chunksize=tamanho_chunk):
                            total_geral += transformar_e_salvar(chunk, ano_arquivo)
            if os.path.exists("temp_contratos.zip"): os.remove("temp_contratos.zip")

    except Exception as e:
        print(f"  ❌ Erro no ficheiro {arq['nome']}: {e}")

# =====================================================================
# 5. A GUILHOTINA (DEDUPLICAÇÃO FINAL NO BANCO DE DADOS)
# =====================================================================
print("\n🧹 Executando a Guilhotina SQL (Eliminando clones absolutos do banco)...")
query_dedup = text("""
    DELETE FROM contratos_licitacoes
    WHERE ctid NOT IN (
        SELECT min(ctid)
        FROM contratos_licitacoes
        GROUP BY numero_contrato, cnpj_cpf_contratado, valor_contrato, data_assinatura, nome_orgao
    );
""")

with engine.connect() as conexao:
    resultado = conexao.execute(query_dedup)
    linhas_deletadas = resultado.rowcount
    conexao.commit()

if linhas_deletadas > 0:
    print(f"   -> 🗑️ Sucesso! Foram encontradas e deletadas {linhas_deletadas} linhas duplicadas enviadas pela API.")
else:
    print("   -> ✨ Nenhum dado duplicado encontrado. A base está perfeita!")

print(f"\n🎉 BASE DE DADOS PRONTA! Total final: {total_geral - linhas_deletadas} contratos únicos.")