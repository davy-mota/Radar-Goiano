import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import plotly.graph_objects as go
from urllib.parse import quote_plus

# =====================================================================
# 1. CONFIGURAÇÕES DA PÁGINA
# =====================================================================
st.set_page_config(page_title="TCC - Transparência Goiás", layout="wide", page_icon="🏛️")
st.title("🏛️ Painel de Transparência - Estado de Goiás")
st.markdown("Análise focada em **PAGAMENTOS REAIS** (dinheiro efetivamente desembolsado pelo Estado).")

@st.cache_resource
def conectar_banco():
    senha_segura = quote_plus("gatodebotas") # <-- NÃO ESQUEÇA DE COLOCAR SUA SENHA
    engine = create_engine(f'postgresql://postgres:{senha_segura}@localhost:5432/gastos_governamentais') # <-- E O NOME DO SEU BANCO
    return engine

engine = conectar_banco()

# =====================================================================
# 2. CONSULTA AO BANCO (Trazendo Empenhos e Pagamentos)
# =====================================================================
@st.cache_data
def carregar_dados_avancados():
    query = """
    SELECT 
        ano_exercicio, 
        nome_orgao,
        COALESCE(funcao, 'NÃO INFORMADA') as funcao,
        COALESCE(nome_credor, 'NÃO INFORMADO') as nome_credor,
        SUM(valor_empenhado) as total_empenhado,
        SUM(valor_pago) as total_pago
    FROM empenhos_pagamentos 
    WHERE ano_exercicio > 2000
    GROUP BY ano_exercicio, nome_orgao, funcao, nome_credor;
    """
    return pd.read_sql(query, engine)

with st.spinner('Extraindo inteligência do banco de dados...'):
    df_completo = carregar_dados_avancados()

# =====================================================================
# 3. BARRA LATERAL (Filtros Avançados)
# =====================================================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Bandeira_de_Goi%C3%A1s.svg/300px-Bandeira_de_Goi%C3%A1s.svg.png", width=150)
st.sidebar.header("Filtros de Pesquisa")

# Filtro de Ano
ano_min, ano_max = int(df_completo['ano_exercicio'].min()), int(df_completo['ano_exercicio'].max())
anos_selecionados = st.sidebar.slider("Período de Análise:", ano_min, ano_max, (ano_min, ano_max))

# Filtro de Órgão
lista_orgaos = ["Todos os Órgãos"] + sorted(df_completo['nome_orgao'].dropna().unique().tolist())
orgao_selecionado = st.sidebar.selectbox("Selecione um Órgão/Secretaria:", lista_orgaos)

# Aplica os filtros
df_filtrado = df_completo[
    (df_completo['ano_exercicio'] >= anos_selecionados[0]) & 
    (df_completo['ano_exercicio'] <= anos_selecionados[1])
]

if orgao_selecionado != "Todos os Órgãos":
    df_filtrado = df_filtrado[df_filtrado['nome_orgao'] == orgao_selecionado]

# =====================================================================
# 4. INTELIGÊNCIA DE DADOS (KPIs Globais)
# =====================================================================
total_empenhado = df_filtrado['total_empenhado'].sum()
total_pago = df_filtrado['total_pago'].sum()
taxa_pagamento = (total_pago / total_empenhado * 100) if total_empenhado > 0 else 0

st.divider()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Dinheiro Realmente Pago", f"R$ {total_pago/1e9:.2f} Bi") # <-- Agora o Pago é o principal
col2.metric("Promessa Inicial (Empenhado)", f"R$ {total_empenhado/1e9:.2f} Bi")
col3.metric("Taxa de Pagamento (Concretizado)", f"{taxa_pagamento:.1f}%")
col4.metric("Qtd. de Fornecedores Pagos", f"{df_filtrado[df_filtrado['total_pago'] > 0]['nome_credor'].nunique():,}".replace(',', '.'))
st.divider()

# =====================================================================
# 5. ORGANIZAÇÃO EM ABAS (TABS)
# =====================================================================
aba1, aba2, aba3 = st.tabs(["📈 Histórico de Pagamentos", "🏆 Top Fornecedores Pagos", "🎯 Áreas Financiadas (Função)"])

# --- ABA 1: EVOLUÇÃO (Focado no Pagamento) ---
with aba1:
    st.subheader("Evolução do Desembolso Real do Estado")
    df_ano = df_filtrado.groupby('ano_exercicio')[['total_empenhado', 'total_pago']].sum().reset_index()
    df_ano['total_empenhado_bi'] = df_ano['total_empenhado'] / 1e9
    df_ano['total_pago_bi'] = df_ano['total_pago'] / 1e9

    fig_evolucao = go.Figure()
    # Inverti a ordem para o Pagamento (verde) chamar mais atenção
    fig_evolucao.add_trace(go.Bar(x=df_ano['ano_exercicio'], y=df_ano['total_pago_bi'], name='Valor Pago (Realidade)', marker_color='#2ca02c'))
    fig_evolucao.add_trace(go.Bar(x=df_ano['ano_exercicio'], y=df_ano['total_empenhado_bi'], name='Valor Empenhado (Promessa)', marker_color='#1f77b4', opacity=0.6))
    
    fig_evolucao.update_layout(barmode='group', xaxis=dict(tickmode='linear', dtick=1), yaxis_title="R$ Bilhões")
    st.plotly_chart(fig_evolucao, width='stretch')

# --- ABA 2: FORNECEDORES (Quem levou o dinheiro) ---
with aba2:
    st.subheader("Top 10 Fornecedores que mais receberam recursos pagos")
    df_fornecedores = df_filtrado[~df_filtrado['nome_credor'].str.contains('FOLHA DE PAGAMENTO', na=False, case=False)]
    df_fornecedores = df_fornecedores.groupby('nome_credor')['total_pago'].sum().reset_index()
    # Filtra só quem realmente recebeu > 0
    df_fornecedores = df_fornecedores[df_fornecedores['total_pago'] > 0] 
    df_top10 = df_fornecedores.sort_values(by='total_pago', ascending=False).head(10)
    
    fig_forn = px.bar(df_top10, x='total_pago', y='nome_credor', orientation='h', 
                      labels={'total_pago': 'Total Pago (R$)', 'nome_credor': 'Credor'},
                      text_auto='.2s', color_discrete_sequence=['#2ca02c'])
    fig_forn.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_forn, width='stretch')

# --- ABA 3: ÁREAS DE ATUAÇÃO (Onde o dinheiro foi injetado) ---
with aba3:
    st.subheader("Distribuição do Dinheiro Pago por Área (Função)")
    # Agora a pizza é baseada no VALOR PAGO e não no empenhado!
    df_funcao = df_filtrado[df_filtrado['total_pago'] > 0].groupby('funcao')['total_pago'].sum().reset_index()
    
    fig_funcao = px.pie(df_funcao, values='total_pago', names='funcao', hole=0.4)
    fig_funcao.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_funcao, width='stretch')

# Rodapé com tabela bruta
with st.expander("🔍 Explorar Banco de Dados Bruto (Filtrado)"):
    st.dataframe(df_filtrado.sort_values(by='total_pago', ascending=False).head(1000))