import pandas as pd
import json
from database import engine
import os
from sklearn.ensemble import IsolationForest

# ==============================================================================
# FUNÇÃO DA INTELIGÊNCIA ARTIFICIAL
# ==============================================================================
def aplicar_ia_anomalias(df, coluna_valor, contaminacao=0.01):
    """Treina a IA e devolve os itens com desvio padrão severo (Outliers)"""
    if df.empty: return pd.DataFrame()
    
    modelo = IsolationForest(n_estimators=100, contamination=contaminacao, random_state=42)
    dados_ia = df[[coluna_valor]].fillna(0)
    df['anomalia_ia'] = modelo.fit_predict(dados_ia)
    
    suspeitos = df[df['anomalia_ia'] == -1].sort_values(by=coluna_valor, ascending=False).head(5)
    return suspeitos

# ==============================================================================
# MOTOR PRINCIPAL DE GERAÇÃO
# ==============================================================================
def gerar_caches_completos():
    anos = ["todos"] + list(range(2013, 2027))
    
    # 1. CRIAÇÃO DA PASTA AUTOMÁTICA
    pasta_raiz = os.path.dirname(__file__)
    pasta_destino = os.path.join(pasta_raiz, "dados_gerados")
    os.makedirs(pasta_destino, exist_ok=True)
    
    print(f"📁 Pasta de destino configurada: {pasta_destino}")

    for ano in anos:
        print(f"\n=========================================")
        print(f"⏳ PROCESSANDO DADOS E IA: Exercício {ano}")
        print(f"=========================================")
        
        wc = f"WHERE ano_exercicio = {ano}" if ano != "todos" else ""
        wc_and = f"AND ano_exercicio = {ano}" if ano != "todos" else ""

        try:
            # ---------------------------------------------------------
            # 1. CACHE DE CONTRATOS + IA
            # ---------------------------------------------------------
            print("-> Gerando cache de Contratos...")
            df_c_kpis = pd.read_sql(f"SELECT COALESCE(SUM(valor_contrato), 0) as total, COUNT(*) as qtd FROM contratos_licitacoes {wc}", engine)
            df_c_top = pd.read_sql(f"SELECT nome_contratado as nome, SUM(valor_contrato) as valor FROM contratos_licitacoes {wc} GROUP BY nome_contratado ORDER BY valor DESC LIMIT 10", engine)
            
            # Buscando dados crus para a IA treinar
            df_c_raw = pd.read_sql(f"SELECT nome_contratado, valor_contrato as valor FROM contratos_licitacoes {wc}", engine)
            suspeitos_c = aplicar_ia_anomalias(df_c_raw, 'valor', contaminacao=0.02)
            
            alertas_ia_contratos = []
            for _, row in suspeitos_c.iterrows():
                alertas_ia_contratos.append({
                    "nome": row['nome_contratado'],
                    "orgao": "Não especificado", # Preenchimento padrão caso não tenha na query
                    "valor": float(row['valor']),
                    "motivo": "Valor de contrato atípico (Outlier) detectado pela IA"
                })

            c_total = float(df_c_kpis['total'][0])
            c_qtd = int(df_c_kpis['qtd'][0])
            c_ticket = c_total / c_qtd if c_qtd > 0 else 0

            with open(os.path.join(pasta_destino, f'cache_contratos_{ano}.json'), 'w', encoding='utf-8') as f:
                json.dump({
                    "kpis": {"valor_total": c_total, "qtd_contratos": c_qtd, "ticket_medio": c_ticket}, 
                    "top_fornecedores": df_c_top.to_dict(orient="records"),
                    "alertas_ia": alertas_ia_contratos
                }, f, ensure_ascii=False, indent=4)

            # ---------------------------------------------------------
            # 2. CACHE DE FOLHA DE PAGAMENTO + IA
            # ---------------------------------------------------------
            print("-> Gerando cache de Folha de Pagamento...")
            df_f_kpis = pd.read_sql(f"SELECT COALESCE(SUM(valor_remuneracao_bruta), 0) as total, COUNT(id) as qtd, COALESCE(AVG(valor_remuneracao_bruta), 0) as media FROM folha_pagamento WHERE valor_remuneracao_bruta > 0 {wc_and}", engine)
            df_f_top = pd.read_sql(f"SELECT nome_servidor as nome, valor_remuneracao_bruta as valor FROM folha_pagamento {wc} ORDER BY valor_remuneracao_bruta DESC LIMIT 5", engine)
            df_f_orgaos = pd.read_sql(f"SELECT nome_orgao as name, SUM(valor_remuneracao_bruta) as value FROM folha_pagamento {wc} GROUP BY nome_orgao ORDER BY value DESC LIMIT 5", engine)

            # Buscando dados crus para a IA treinar
            df_f_raw = pd.read_sql(f"SELECT nome_servidor, nome_orgao, valor_remuneracao_bruta as valor FROM folha_pagamento WHERE valor_remuneracao_bruta > 0 {wc_and}", engine)
            suspeitos_f = aplicar_ia_anomalias(df_f_raw, 'valor', contaminacao=0.01)
            
            alertas_ia_folha = []
            for _, row in suspeitos_f.iterrows():
                alertas_ia_folha.append({
                    "nome": row['nome_servidor'],
                    "orgao": row['nome_orgao'],
                    "valor": float(row['valor']),
                    "motivo": "Salário com desvio estatístico severo detectado pela IA"
                })

            f_total = float(df_f_kpis['total'][0])
            
            with open(os.path.join(pasta_destino, f'cache_folha_{ano}.json'), 'w', encoding='utf-8') as f:
                json.dump({
                    "kpis": {"total_folha": f_total, "qtd_servidores": int(df_f_kpis['qtd'][0]), "media_salarial": float(df_f_kpis['media'][0])}, 
                    "top_salarios": df_f_top.to_dict(orient="records"), 
                    "distribuicao": df_f_orgaos.to_dict(orient="records"),
                    "alertas_ia": alertas_ia_folha
                }, f, ensure_ascii=False, indent=4)

            # ---------------------------------------------------------
            # 3. CACHE DE DIÁRIAS + IA
            # ---------------------------------------------------------
            print("-> Gerando cache de Diárias...")
            df_d_kpis = pd.read_sql(f"SELECT COALESCE(SUM(valor_total), 0) as total, COUNT(id) as qtd, COALESCE(MAX(valor_total), 0) as maior FROM diarias_passagens {wc}", engine)
            df_d_top_v = pd.read_sql(f"SELECT nome_servidor as nome, SUM(valor_total) as valor FROM diarias_passagens {wc} GROUP BY nome_servidor ORDER BY valor DESC LIMIT 5", engine)
            df_d_top_d = pd.read_sql(f"SELECT destino as name, SUM(valor_total) as value FROM diarias_passagens {wc} GROUP BY destino ORDER BY value DESC LIMIT 5", engine)

            # Buscando dados crus para a IA treinar
            df_d_raw = pd.read_sql(f"SELECT nome_servidor, destino as nome_orgao, valor_total as valor FROM diarias_passagens {wc}", engine)
            suspeitos_d = aplicar_ia_anomalias(df_d_raw, 'valor', contaminacao=0.01)
            
            alertas_ia_diarias = []
            for _, row in suspeitos_d.iterrows():
                alertas_ia_diarias.append({
                    "nome": row['nome_servidor'],
                    "orgao": row['nome_orgao'],
                    "valor": float(row['valor']),
                    "motivo": "Gasto com diária estatisticamente acima do padrão estadual"
                })

            d_total = float(df_d_kpis['total'][0])
            
            with open(os.path.join(pasta_destino, f'cache_diarias_{ano}.json'), 'w', encoding='utf-8') as f:
                json.dump({
                    "kpis": {"total_gasto": d_total, "qtd_viagens": int(df_d_kpis['qtd'][0]), "maior_diaria": float(df_d_kpis['maior'][0])}, 
                    "top_viajantes": df_d_top_v.to_dict(orient="records"), 
                    "top_destinos": df_d_top_d.to_dict(orient="records"),
                    "alertas_ia": alertas_ia_diarias
                }, f, ensure_ascii=False, indent=4)

            # ---------------------------------------------------------
            # 4. CACHE DE VISÃO GERAL (Cruza tudo + Radar da IA)
            # ---------------------------------------------------------
            print("-> Gerando cache de Visão Geral...")
            df_g_orgaos = pd.read_sql(f"SELECT nome_orgao as nome, SUM(valor) as total FROM (SELECT nome_orgao, valor_remuneracao_bruta as valor FROM folha_pagamento {wc} UNION ALL SELECT nome_orgao, valor_total as valor FROM diarias_passagens {wc}) as gastos GROUP BY nome_orgao ORDER BY total DESC LIMIT 5", engine)
            df_g_contrato = pd.read_sql(f"SELECT COALESCE(MAX(valor_contrato), 0) as maximo FROM contratos_licitacoes {wc}", engine)
            df_g_teto = pd.read_sql(f"SELECT COUNT(*) as qtd FROM folha_pagamento WHERE valor_remuneracao_bruta > 41650.92 {wc_and}", engine)
            df_g_viajante = pd.read_sql(f"SELECT nome_servidor as nome, SUM(valor_total) as valor FROM diarias_passagens {wc} GROUP BY nome_servidor ORDER BY valor DESC LIMIT 1", engine)
            df_g_empresa = pd.read_sql(f"SELECT nome_contratado as nome, COUNT(*) as qtd FROM contratos_licitacoes {wc} GROUP BY nome_contratado ORDER BY qtd DESC LIMIT 1", engine)

            custo_total = c_total + f_total + d_total
            
            # Coleta as maiores bizarrices de cada categoria para o resumo
            radar_riscos = []
            if alertas_ia_folha: radar_riscos.append({**alertas_ia_folha[0], "tipo": "Folha"})
            if alertas_ia_contratos: radar_riscos.append({**alertas_ia_contratos[0], "tipo": "Contratos"})
            if alertas_ia_diarias: radar_riscos.append({**alertas_ia_diarias[0], "tipo": "Diárias"})

            with open(os.path.join(pasta_destino, f'cache_visao_geral_{ano}.json'), 'w', encoding='utf-8') as f:
                json.dump({
                    "kpis": {
                        "custo_total": custo_total,
                        "orgao_campeao": df_g_orgaos.iloc[0]['nome'] if not df_g_orgaos.empty else "N/A",
                        "maior_despesa": float(df_g_contrato['maximo'][0]),
                        "alerta_teto": int(df_g_teto['qtd'][0])
                    },
                    "raio_x": [{"name": "Folha", "value": f_total}, {"name": "Contratos", "value": c_total}, {"name": "Diárias", "value": d_total}],
                    "top_orgaos": df_g_orgaos.to_dict(orient="records"),
                    "anomalias": {
                        "maior_viajante": {"nome": df_g_viajante['nome'][0], "valor": float(df_g_viajante['valor'][0])} if not df_g_viajante.empty else {"nome": "N/A", "valor": 0},
                        "empresa_favorita": {"nome": df_g_empresa['nome'][0], "qtd": int(df_g_empresa['qtd'][0])} if not df_g_empresa.empty else {"nome": "N/A", "qtd": 0}
                    },
                    "radar_ia_geral": radar_riscos
                }, f, ensure_ascii=False, indent=4)

            print(f"✅ Arquivos de {ano} salvos com sucesso na pasta 'dados_gerados'!")

        except Exception as e:
            print(f"❌ ERRO ao gerar dados de {ano}: {str(e)}")

if __name__ == "__main__":
    gerar_caches_completos()