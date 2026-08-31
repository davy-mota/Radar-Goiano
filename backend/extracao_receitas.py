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
    "ano_exercicio", "mes_exercicio", "nome_orgao", "categoria_receita", 
    "origem_receita", "valor_previsto", "valor_arrecadado", "data_arrecadacao"
]

# =====================================================================
# 2. SELECIONANDO OS ALVOS (RECEITAS)
# =====================================================================
print("🔍 Buscando links da base de RECEITAS no portal de Goiás...")
url_catalogo = "https://dadosabertos.go.gov.br/api/3/action/package_show?id=receitas-detalhadas"

resposta = requests.get(url_catalogo)
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
# 3. FUNÇÃO DE LIMPEZA E MAPEAMENTO (CAÇADOR DE MESES ATUALIZADO)
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

    # 🔥 CAÇADORES: Procurando as colunas de tempo
    col_data = achar_coluna(['DATAARRECADACAO', 'DATA', 'DATALANCAMENTO'])
    col_anomes = achar_coluna(['ANOMES']) # Ex: 202511
    col_ano = achar_coluna(['EXERCICIO', 'ANOEXERCICIO', 'ANO'])
    col_mes = achar_coluna(['MES', 'MÊS', 'MESEXERCICIO']) # Ex: Novembro ou 11

    if col_data:
        # Se a data completa existir, ele extrai tudo dela
        datas_limpas = df_lote[col_data].astype(str).str[:10]
        datas = pd.to_datetime(datas_limpas, errors='coerce')
        df_lote['ano_exercicio'] = datas.dt.year.fillna(0).astype(int)
        df_lote['mes_exercicio'] = datas.dt.month.fillna(0).astype(int)
        df_lote['data_arrecadacao'] = datas.dt.strftime('%Y-%m-%d').where(datas.notna(), None)
    else:
        # Se não tem data, vamos montar o quebra-cabeça do Ano
        if col_anomes:
            df_lote['ano_exercicio'] = pd.to_numeric(df_lote[col_anomes].astype(str).str[:4], errors='coerce').fillna(0).astype(int)
        elif col_ano:
            df_lote['ano_exercicio'] = pd.to_numeric(df_lote[col_ano], errors='coerce').fillna(0).astype(int)
        else:
            df_lote['ano_exercicio'] = 0

        # E agora o quebra-cabeça do Mês
        if col_anomes:
            df_lote['mes_exercicio'] = pd.to_numeric(df_lote[col_anomes].astype(str).str[4:6], errors='coerce').fillna(0).astype(int)
        elif col_mes:
            # Dicionário tradutor caso o mês esteja escrito por extenso
            meses_map = {
                'JANEIRO': 1, 'FEVEREIRO': 2, 'MARÇO': 3, 'MARCO': 3,
                'ABRIL': 4, 'MAIO': 5, 'JUNHO': 6, 'JULHO': 7,
                'AGOSTO': 8, 'SETEMBRO': 9, 'OUTUBRO': 10,
                'NOVEMBRO': 11, 'DEZEMBRO': 12
            }
            def limpa_mes(m):
                m_str = str(m).strip().upper()
                if m_str.isdigit(): return int(m_str)
                return meses_map.get(m_str, 0)
            df_lote['mes_exercicio'] = df_lote[col_mes].apply(limpa_mes)
        else:
            df_lote['mes_exercicio'] = 0
            
        df_lote['data_arrecadacao'] = None

    # Segurança caso as colunas originais também falhem o ano
    if ano_do_arquivo > 0:
        df_lote.loc[df_lote['ano_exercicio'] == 0, 'ano_exercicio'] = ano_do_arquivo

    # Textos
    col_orgao = achar_coluna(['NOMEORGAO', 'ORGAO'])
    col_cat = achar_coluna(['CATEGORIA', 'CATEGORIAECONOMICA', 'CODIGODACATEGORIAECONOMICA'])
    col_origem = achar_coluna(['ORIGEM', 'ORIGEMRECEITA'])
    
    df_lote['nome_orgao'] = df_lote[col_orgao] if col_orgao else 'NÃO INFORMADO'
    df_lote['categoria_receita'] = df_lote[col_cat] if col_cat else 'NÃO INFORMADA'
    df_lote['origem_receita'] = df_lote[col_origem] if col_origem else 'NÃO INFORMADA'

    # Valores
    col_previsto = achar_coluna(['RECEITAPREVISTALOA', 'VALORPREVISTO', 'PREVISAO', 'PREVISTO'])
    col_arrecadado = achar_coluna(['RECEITAREALIZADA', 'VALORARRECADADO', 'ARRECADADO', 'REALIZADO', 'VALOR'])

    def limpar_moeda_universal(serie):
        s = serie.astype(str).str.strip().str.replace('"', '', regex=False).str.replace("'", "", regex=False)
        def converte_valor(val):
            if val.lower() == 'nan' or val == 'none' or val == '': return 0.0
            if ',' in val:
                val = val.replace('.', '')
                val = val.replace(',', '.')
            else:
                if val.count('.') > 1:
                    val = val.replace('.', '')
            try:
                return float(val)
            except:
                return 0.0
        return s.apply(converte_valor)

    df_lote['valor_previsto'] = limpar_moeda_universal(df_lote[col_previsto]) if col_previsto else 0
    df_lote['valor_arrecadado'] = limpar_moeda_universal(df_lote[col_arrecadado]) if col_arrecadado else 0

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
            
            resposta_csv = requests.get(arq['url'])
            with open("temp_arquivo.csv", "wb") as f:
                f.write(resposta_csv.content)
            
            with open("temp_arquivo.csv", "r", encoding='latin1') as f:
                primeira_linha = f.readline()
                separador = ';' if ';' in primeira_linha else ','
                print(f"      [🔍] Separador detectado: '{separador}'")
                
            df_temp = pd.read_csv("temp_arquivo.csv", sep=separador, encoding='latin1', dtype=str, on_bad_lines='skip')
            linhas_salvas = transformar_e_salvar(df_temp, ano_arquivo)
            total_geral += linhas_salvas
            os.remove("temp_arquivo.csv")
            print(f"  ✅ Salvo! +{linhas_salvas} registros.")

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
                        primeira_linha = f_csv.readline().decode('latin1', errors='ignore')
                        separador = ';' if ';' in primeira_linha else ','
                        f_csv.seek(0)
                        
                        for chunk in pd.read_csv(f_csv, sep=separador, encoding='latin1', dtype=str, on_bad_lines='skip', chunksize=tamanho_chunk):
                            linhas_salvas = transformar_e_salvar(chunk, ano_arquivo)
                            total_geral += linhas_salvas
                            print(f"      Lote processado. Acumulado: {total_geral}")
                            
            if os.path.exists("temp_receitas.zip"): os.remove("temp_receitas.zip")

    except Exception as e:
        print(f"  ❌ Erro no arquivo {arq['nome']}: {e}")

print(f"\n🎉 NOVO BANCO PRONTO! Total de {total_geral} receitas salvas.")
