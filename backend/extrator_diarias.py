import requests
import pandas as pd
from sqlalchemy import text
from database import engine
import zipfile
import os
import re
import sys

# =====================================================================
# 1. CONFIGURAÇÕES
# =====================================================================
colunas_banco = [
    "ano_exercicio", "nome_orgao", "nome_servidor", "cargo", 
    "destino", "motivo_viagem", "valor_diarias", 
    "valor_passagens", "valor_total"
]

# =====================================================================
# 2. SELECIONANDO OS ALVOS (BUSCA INTELIGENTE)
# =====================================================================
print("🔍 Pesquisando ficheiros de DIÁRIAS E PASSAGENS no motor do portal...")

url_busca = "https://dadosabertos.go.gov.br/api/3/action/package_search?q=diaria"

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
    elif ('2003' in nome or '2024' in nome or '2026' in nome or '-' in nome) and formato == 'ZIP':
        arquivos_alvo.append({'nome': nome, 'url': r['url'], 'tipo': 'ZIP'})

if not arquivos_alvo:
    print("⚠️ A busca funcionou, mas não foram encontrados ficheiros compatíveis.")
    sys.exit()

print(f"✅ Sucesso! Encontrados {len(arquivos_alvo)} ficheiros de diárias para descarregar.")

print("🧹 Fonte validada. Preparando a carga sem alterar a tabela oficial...")
with engine.begin() as conexao:
    conexao.execute(text("DROP TABLE IF EXISTS diarias_passagens_staging;"))
    conexao.execute(text("CREATE TABLE diarias_passagens_staging (LIKE diarias_passagens INCLUDING DEFAULTS);"))

# =====================================================================
# 3. FUNÇÃO DE LIMPEZA E MAPEAMENTO (CAÇADOR ATUALIZADO)
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

    # Caça datas e anos (Atualizado com NUMRANO e DATASAIDAVIAGEM)
    col_ano = achar_coluna(['EXERCICIO', 'ANOEXERCICIO', 'ANO', 'ANOREFERENCIA', 'NUMRANO'])
    col_data = achar_coluna(['DATAVIAGEM', 'DATAINICIO', 'DATAPAGAMENTO', 'DATA', 'DATASAIDAVIAGEM'])

    if col_data:
        datas_limpas = df_lote[col_data].astype(str).str[:10]
        datas = pd.to_datetime(datas_limpas, errors='coerce')
        df_lote['ano_exercicio'] = datas.dt.year.fillna(0).astype(int)
    elif col_ano:
        df_lote['ano_exercicio'] = pd.to_numeric(df_lote[col_ano], errors='coerce').fillna(0).astype(int)
    else:
        df_lote['ano_exercicio'] = 0

    if ano_do_arquivo > 0:
        df_lote.loc[df_lote['ano_exercicio'] == 0, 'ano_exercicio'] = ano_do_arquivo

    # Textos da Viagem (Atualizado com novas nomenclaturas)
    col_orgao = achar_coluna(['NOMEORGAO', 'ORGAO', 'SECRETARIA', 'SIGLORGAOSERVIDOR'])
    col_nome_serv = achar_coluna(['NOMESERVIDOR', 'NOME', 'BENEFICIARIO', 'FAVORECIDO'])
    col_cargo = achar_coluna(['CARGO', 'FUNCAO', 'EMPREGO', 'NOMECARGOSERVIDOR'])
    col_destino = achar_coluna(['DESTINO', 'CIDADEDESTINO', 'LOCALIDADE', 'TRECHO', 'DESCDESTINOVIAGEM'])
    col_motivo = achar_coluna(['MOTIVOVIAGEM', 'MOTIVO', 'DESCRICAO', 'JUSTIFICATIVA', 'OBJETIVO', 'DESCMOTIVOVIAGEM'])
    
    df_lote['nome_orgao'] = df_lote[col_orgao] if col_orgao else 'NÃO INFORMADO'
    df_lote['nome_servidor'] = df_lote[col_nome_serv] if col_nome_serv else 'NÃO INFORMADO'
    df_lote['cargo'] = df_lote[col_cargo] if col_cargo else 'NÃO INFORMADO'
    df_lote['destino'] = df_lote[col_destino] if col_destino else 'NÃO INFORMADO'
    df_lote['motivo_viagem'] = df_lote[col_motivo] if col_motivo else 'NÃO INFORMADO'

    # Valores Financeiros (Atualizado com VALRTOTALVIAGEM)
    col_val_diaria = achar_coluna(['VALORDIARIA', 'VALORDIARIAS', 'TOTALDIARIAS'])
    col_val_passagem = achar_coluna(['VALORPASSAGEM', 'VALORPASSAGENS', 'TOTALPASSAGENS'])
    col_val_total = achar_coluna(['VALORTOTAL', 'TOTAL', 'VALORPAGO', 'VALOR', 'VALRTOTALVIAGEM'])

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

    df_lote['valor_diarias'] = limpar_moeda_universal(df_lote[col_val_diaria]) if col_val_diaria else 0
    df_lote['valor_passagens'] = limpar_moeda_universal(df_lote[col_val_passagem]) if col_val_passagem else 0
    df_lote['valor_total'] = limpar_moeda_universal(df_lote[col_val_total]) if col_val_total else 0

    # Gravação no Banco
    for col in colunas_banco:
        if col not in df_lote.columns: df_lote[col] = None
    df_lote = df_lote[colunas_banco]
            
    df_lote.to_sql('diarias_passagens_staging', engine, if_exists='append', index=False)
    return len(df_lote)

# =====================================================================
# 4. MOTOR DE EXTRAÇÃO (DETETOR DE SEPARADORES AUTOMÁTICO)
# =====================================================================
total_geral = 0
erros_extracao = 0
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
            with open("temp_arquivo.csv", "wb") as f:
                f.write(resposta_csv.content)
            
            with open("temp_arquivo.csv", "r", encoding='latin1') as f:
                primeira_linha = f.readline()
                separador = ';' if ';' in primeira_linha else ','
                print(f"      [🔍] Separador detetado: '{separador}'")
                
            df_temp = pd.read_csv("temp_arquivo.csv", sep=separador, encoding='latin1', dtype=str, on_bad_lines='skip')
            linhas_salvas = transformar_e_salvar(df_temp, ano_arquivo)
            total_geral += linhas_salvas
            os.remove("temp_arquivo.csv")
            print(f"  ✅ Guardado! +{linhas_salvas} registos de viagens.")

        elif arq['tipo'] == 'ZIP':
            print("  ⏳ A descarregar o ficheiro ZIP Histórico...")
            resposta_zip = requests.get(arq['url'], stream=True)
            with open("temp_viagens.zip", "wb") as f:
                for pedaço in resposta_zip.iter_content(chunk_size=8192):
                    f.write(pedaço)
            
            with zipfile.ZipFile("temp_viagens.zip", "r") as z:
                csvs_internos = [n for n in z.namelist() if n.upper().endswith('.CSV') and '__MACOSX' not in n.upper() and not n.split('/')[-1].startswith('._')]
                
                for nome_csv in csvs_internos:
                    ano_arquivo = descobrir_ano_no_nome(nome_csv)
                    print(f"    ➡️ A ler: {nome_csv} (Ano: {ano_arquivo})")
                    
                    with z.open(nome_csv) as f_csv:
                        primeira_linha = f_csv.readline().decode('latin1', errors='ignore')
                        separador = ';' if ';' in primeira_linha else ','
                        f_csv.seek(0)
                        
                        for chunk in pd.read_csv(f_csv, sep=separador, encoding='latin1', dtype=str, on_bad_lines='skip', chunksize=tamanho_chunk):
                            linhas_salvas = transformar_e_salvar(chunk, ano_arquivo)
                            total_geral += linhas_salvas
                            print(f"      Lote processado. Acumulado: {total_geral}")
                            
            if os.path.exists("temp_viagens.zip"): os.remove("temp_viagens.zip")

    except Exception as e:
        erros_extracao += 1
        print(f"  ❌ Erro no ficheiro {arq['nome']}: {e}")

if erros_extracao or total_geral == 0:
    with engine.begin() as conexao:
        conexao.execute(text("DROP TABLE IF EXISTS diarias_passagens_staging;"))
    sys.exit("❌ Carga cancelada; a tabela oficial de diárias foi preservada.")

print(f"\n🎉 BASE DE DADOS PRONTA! Total de {total_geral} registos de viagens e diárias guardados.")

# =====================================================================
# 5. A GUILHOTINA (DEDUPLICAÇÃO FINAL DAS DIÁRIAS)
# =====================================================================
print("\n🧹 Executando a Guilhotina SQL (Eliminando clones absolutos de Diárias)...")
query_dedup_diarias = text("""
    DELETE FROM diarias_passagens_staging
    WHERE ctid NOT IN (
        SELECT min(ctid)
        FROM diarias_passagens_staging
        -- Agrupa pelas colunas que identificam uma viagem única
        GROUP BY ano_exercicio, nome_servidor, destino, valor_total
    );
""")

with engine.connect() as conexao:
    resultado = conexao.execute(query_dedup_diarias)
    linhas_deletadas = resultado.rowcount
    conexao.commit()

with engine.begin() as conexao:
    conexao.execute(text("TRUNCATE TABLE diarias_passagens;"))
    conexao.execute(text("""
        INSERT INTO diarias_passagens
            (ano_exercicio, nome_orgao, nome_servidor, cargo, destino,
             motivo_viagem, valor_diarias, valor_passagens, valor_total)
        SELECT ano_exercicio, nome_orgao, nome_servidor, cargo, destino,
               motivo_viagem, valor_diarias, valor_passagens, valor_total
        FROM diarias_passagens_staging;
    """))
    conexao.execute(text("DROP TABLE diarias_passagens_staging;"))

if linhas_deletadas > 0:
    print(f"   -> 🗑️ Sucesso! Foram deletadas {linhas_deletadas} viagens duplicadas enviadas pela API.")
else:
    print("   -> ✨ Nenhum dado duplicado encontrado. A base está perfeita!")
