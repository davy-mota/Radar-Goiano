import requests
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import zipfile
import os
import re
import sys

# =====================================================================
# 1. CONFIGURAÇÕES E CONEXÃO
# =====================================================================
senha_segura = quote_plus("gatodebotas") # <-- COLOQUE SUA SENHA AQUI
engine = create_engine(f'postgresql://postgres:{senha_segura}@localhost:5432/gastos_governamentais') # <-- SEU BANCO

colunas_banco = [
    "ano_exercicio", "mes_exercicio", "nome_orgao", "nome_servidor", 
    "cpf_mascarado", "cargo", "situacao_vinculo", 
    "valor_remuneracao_bruta", "valor_remuneracao_liquida"
]

print("🧹 Limpando dados antigos da Folha para a nova extração (Full Refresh)...")
with engine.connect() as conexao:
    conexao.execute(text("TRUNCATE TABLE folha_pagamento;"))
    conexao.commit()

# 🔥 NOVO: LIMPEZA AUTOMÁTICA (CARGA FULL) PARA EVITAR DUPLICIDADE
print("🧹 Limpando a tabela 'folha_pagamento' para evitar dados duplicados...")
try:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE folha_pagamento RESTART IDENTITY CASCADE;"))
    print("✨ Tabela limpa e pronta para receber os dados!")
except Exception as e:
    print(f"⚠️ Aviso ao tentar limpar a tabela: {e}")

    

# =====================================================================
# 2. SELECIONANDO OS ALVOS (BUSCA INTELIGENTE)
# =====================================================================
print("🔍 Pesquisando ficheiros de FOLHA DE PAGAMENTO no motor do portal...")

url_busca = "https://dadosabertos.go.gov.br/api/3/action/package_search?q=folha"

try:
    resposta = requests.get(url_busca)
    
    if resposta.status_code != 200:
        print(f"❌ O portal retornou um erro. Status: {resposta.status_code}")
        sys.exit() 
        
    dados_json = resposta.json()
    pacotes = dados_json.get('result', {}).get('results', [])
    
    recursos = []
    for pacote in pacotes:
        recursos.extend(pacote.get('resources', []))
        
except Exception as e:
    print(f"❌ Erro de ligação à internet: {e}")
    sys.exit()

arquivos_alvo = []
for r in recursos:
    nome = r.get('name', '')
    formato = r.get('format', '').upper()
    
    if 'CONSOLIDADO' in nome or 'GERAL' in nome or 'TODOS' in nome or 'COMPLETO' in nome:
        print(f"   -> 🛑 Ignorando arquivo consolidado para evitar duplicidade: {nome}")
        continue

    if '2025' in nome and formato == 'CSV':
        arquivos_alvo.append({'nome': nome, 'url': r['url'], 'tipo': 'CSV'})
    
    elif ('2003' in nome or '2024' in nome or '-' in nome) and formato == 'ZIP':
        arquivos_alvo.append({'nome': nome, 'url': r['url'], 'tipo': 'ZIP'})

if not arquivos_alvo:
    print("⚠️ A busca funcionou, mas não foram encontrados ficheiros compatíveis.")
    sys.exit()

print(f"✅ Sucesso! Encontrados {len(arquivos_alvo)} ficheiros de folha de pagamento.")

# =====================================================================
# 3. FUNÇÃO DE LIMPEZA E MAPEAMENTO 
# =====================================================================
def transformar_e_salvar(df_lote, ano_do_arquivo):
    colunas_originais = df_lote.columns
    colunas_limpas = colunas_originais.str.replace(r'[^a-zA-Z0-9]', '', regex=True).str.upper()
    mapa_colunas = dict(zip(colunas_limpas, colunas_originais))
    
    def achar_coluna(possibilidades):
        for p in possibilidades:
            if p in mapa_colunas:
                return mapa_colunas[p]
        return None

    # Caça Ano e Mês (Ajustado para lidar com espaços ou decimais invisíveis)
    col_anomes = achar_coluna(['ANOMES', 'ANO_MES'])
    col_ano = achar_coluna(['EXERCICIO', 'ANOEXERCICIO', 'ANO'])
    col_mes = achar_coluna(['MES', 'MESEXERCICIO'])

    if col_anomes:
        s_anomes = df_lote[col_anomes].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        df_lote['ano_exercicio'] = pd.to_numeric(s_anomes.str[:4], errors='coerce').fillna(0).astype(int)
        df_lote['mes_exercicio'] = pd.to_numeric(s_anomes.str[4:6], errors='coerce').fillna(0).astype(int)
    else:
        df_lote['ano_exercicio'] = pd.to_numeric(df_lote[col_ano], errors='coerce').fillna(0).astype(int) if col_ano else 0
        df_lote['mes_exercicio'] = pd.to_numeric(df_lote[col_mes], errors='coerce').fillna(0).astype(int) if col_mes else 0

    if ano_do_arquivo > 0:
        df_lote.loc[df_lote['ano_exercicio'] == 0, 'ano_exercicio'] = ano_do_arquivo

    # Textos
    col_orgao = achar_coluna(['ORGAO', 'NOMEORGAO', 'SECRETARIA'])
    col_nome = achar_coluna(['NOMESERVIDOR', 'NOME', 'SERVIDOR'])
    col_cargo = achar_coluna(['NOMECARGO', 'CARGO', 'FUNCAO'])
    col_vinculo = achar_coluna(['SIMBOLOCARGO', 'VINCULO', 'TIPO', 'SITUACAO', 'SITUACAOVINCULO'])
    col_cpf = achar_coluna(['CPF', 'CPFMASCARADO', 'CPFSERVIDOR'])
    
    df_lote['nome_orgao'] = df_lote[col_orgao] if col_orgao else 'NÃO INFORMADO'
    df_lote['nome_servidor'] = df_lote[col_nome] if col_nome else 'NÃO INFORMADO'
    df_lote['cargo'] = df_lote[col_cargo] if col_cargo else 'NÃO INFORMADO'
    df_lote['situacao_vinculo'] = df_lote[col_vinculo] if col_vinculo else 'NÃO INFORMADA'
    df_lote['cpf_mascarado'] = df_lote[col_cpf].astype(str).replace({'nan': None}) if col_cpf else None

    # Valores Financeiros
    col_bruto = achar_coluna(['VALORPROVENTO', 'VALORBRUTO', 'REMUNERACAOBRUTA', 'PROVENTO'])
    col_liquido = achar_coluna(['VALORLIQUIDO', 'LIQUIDO', 'REMUNERACAOLIQUIDA'])

    def limpar_moeda_universal(serie):
        s = serie.astype(str).str.strip().str.replace('"', '', regex=False).str.replace("'", "", regex=False)
        def converte_valor(val):
            if val.lower() == 'nan' or val == 'none' or val == '': return 0.0
            if ',' in val:
                val = val.replace('.', '').replace(',', '.')
            else:
                if val.count('.') > 1:
                    val = val.replace('.', '')
            try:
                return float(val)
            except:
                return 0.0
        return s.apply(converte_valor)

    df_lote['valor_remuneracao_bruta'] = limpar_moeda_universal(df_lote[col_bruto]) if col_bruto else 0
    df_lote['valor_remuneracao_liquida'] = limpar_moeda_universal(df_lote[col_liquido]) if col_liquido else 0

    # Gravação no Banco
    for col in colunas_banco:
        if col not in df_lote.columns: df_lote[col] = None
    df_lote = df_lote[colunas_banco]
            
    df_lote.to_sql('folha_pagamento', engine, if_exists='append', index=False)
    return len(df_lote)

# =====================================================================
# 4. MOTOR DE EXTRAÇÃO 
# =====================================================================
total_geral = 0
tamanho_chunk = 150000

def descobrir_ano_no_nome(texto):
    match = re.search(r'(20\d{2})', texto)
    return int(match.group(1)) if match else 0

for arq in arquivos_alvo:
    print(f"\n🚀 A Iniciar Extração da Folha: {arq['nome']} ...")
    try:
        if arq['tipo'] == 'CSV':
            ano_arquivo = descobrir_ano_no_nome(arq['nome'])
            
            resposta_csv = requests.get(arq['url'])
            with open("temp_arquivo.csv", "wb") as f:
                f.write(resposta_csv.content)
            
            with open("temp_arquivo.csv", "r", encoding='latin1') as f:
                primeira_linha = f.readline()
                separador = ';' if ';' in primeira_linha else ','
                print(f"      [🔍] Separador detetado: '{separador}'")
                
            for chunk in pd.read_csv("temp_arquivo.csv", sep=separador, encoding='latin1', dtype=str, on_bad_lines='skip', chunksize=tamanho_chunk):
                linhas_salvas = transformar_e_salvar(chunk, ano_arquivo)
                total_geral += linhas_salvas
                print(f"      Lote processado. Acumulado: {total_geral} salários registados.")
                
            os.remove("temp_arquivo.csv")
            print(f"  ✅ Ficheiro de {ano_arquivo} guardado!")

        elif arq['tipo'] == 'ZIP':
            print("  ⏳ A descarregar a Folha Histórica (Isto pode demorar alguns minutos)...")
            resposta_zip = requests.get(arq['url'], stream=True)
            with open("temp_folha.zip", "wb") as f:
                for pedaço in resposta_zip.iter_content(chunk_size=8192):
                    f.write(pedaço)
            
            with zipfile.ZipFile("temp_folha.zip", "r") as z:
                csvs_internos = [n for n in z.namelist() if n.upper().endswith('.CSV') and '__MACOSX' not in n.upper() and not n.split('/')[-1].startswith('._')]
                
                for nome_csv in csvs_internos:
                    ano_arquivo = descobrir_ano_no_nome(nome_csv)
                    print(f"    ➡️ A ler o ficheiro: {nome_csv}")
                    
                    # 🔥 CORREÇÃO: Abre uma vez apenas para descobrir o separador e fecha!
                    with z.open(nome_csv) as f_csv_temp:
                        primeira_linha = f_csv_temp.readline().decode('latin1', errors='ignore')
                        separador = ';' if ';' in primeira_linha else ','
                    
                    # Abre a segunda vez para o Pandas ler desde a primeira linha (cabeçalho intacto)
                    with z.open(nome_csv) as f_csv:
                        for chunk in pd.read_csv(f_csv, sep=separador, encoding='latin1', dtype=str, on_bad_lines='skip', chunksize=tamanho_chunk):
                            linhas_salvas = transformar_e_salvar(chunk, ano_arquivo)
                            total_geral += linhas_salvas
                            print(f"      Lote pesado processado. Acumulado Geral: {total_geral}")
                            
            if os.path.exists("temp_folha.zip"): os.remove("temp_folha.zip")

    except Exception as e:
        print(f"  ❌ Erro no ficheiro {arq['nome']}: {e}")

print(f"\n🎉 DATA LAKE FINALIZADO! Total impressionante de {total_geral} contracheques guardados.")

# =====================================================================
# 5. A GUILHOTINA (DEDUPLICAÇÃO FINAL DA FOLHA)
# =====================================================================
print("\n🧹 Executando a Guilhotina SQL (Eliminando clones absolutos da Folha)...")
query_dedup_folha = text("""
    DELETE FROM folha_pagamento
    WHERE ctid NOT IN (
        SELECT min(ctid)
        FROM folha_pagamento
        -- Agrupa pelas colunas que, juntas, provam que é exatamente o mesmo salário
        GROUP BY ano_exercicio, nome_servidor, nome_orgao, valor_remuneracao_bruta
    );
""")

with engine.connect() as conexao:
    resultado = conexao.execute(query_dedup_folha)
    linhas_deletadas = resultado.rowcount
    conexao.commit()

if linhas_deletadas > 0:
    print(f"   -> 🗑️ Sucesso! Foram deletadas {linhas_deletadas} linhas duplicadas enviadas pela API.")
else:
    print("   -> ✨ Nenhum dado duplicado encontrado. A base está perfeita!")