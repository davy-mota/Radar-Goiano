import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
from urllib.parse import quote_plus

# =====================================================================
# 1. CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira linha do Streamlit)
# =====================================================================
st.set_page_config(page_title="Radar Goiano | TCC", page_icon="👁️", layout="wide", initial_sidebar_state="expanded")

# =====================================================================
# 2. CONEXÃO COM O BANCO DE DADOS (Com Cache para velocidade)
# =====================================================================
senha_segura = quote_plus("gatodebotas") # <-- NÃO ESQUEÇA DE COLOCAR SUA SENHA
engine = create_engine(f'postgresql://postgres:{senha_segura}@localhost:5432/gastos_governamentais') # <-- E O NOME DO SEU BANCO

@st.cache_data(ttl=3600) # Mantém os dados na memória por 1 hora para não travar o banco
def carregar_dados(query):
    return pd.read_sql(query, engine)

# =====================================================================
# 3. O "CSS HACK" PARA O VISUAL MODERNO (DARK SAAS)
# =====================================================================
st.markdown("""
    <style>
    /* Fundo principal bem escuro */
    .stApp {
        background-color: #0E1117;
    }
    
    /* Esconde o menu do Streamlit (hambúrguer) e o rodapé */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Estilizando os Cards de Métrica Customizados */
    .metric-card {
        background-color: #1A1C23;
        border: 1px solid #2E323E;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #00D4FF; /* Azul Neon */
        margin: 0;
    }
    .metric-label {
        font-size: 1rem;
        color: #8B949E;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 5px;
    }
    
    /* Título principal brilhante */
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #8A2BE2, #00D4FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 4. MENU LATERAL (SIDEBAR)
# =====================================================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Bandeira_de_Goi%C3%A1s.svg/320px-Bandeira_de_Goi%C3%A1s.svg.png", width=150)
st.sidebar.markdown("## 👁️ Radar Goiano")
st.sidebar.markdown("Auditoria de Contas Públicas")
st.sidebar.markdown("---")
aba_selecionada = st.sidebar.radio("Navegação do Painel:", ["📊 Visão Geral", "💼 Contratos e Licitações", "✈️ Diárias e Viagens", "👥 Folha de Pagamento"])

# Cores Neon para os gráficos
cores_neon = ['#00D4FF', '#8A2BE2', '#00FA9A', '#FF007F', '#FFA500']

# =====================================================================
# 5. TELA: CONTRATOS E LICITAÇÕES
# =====================================================================
if aba_selecionada == "💼 Contratos e Licitações":
    st.markdown('<p class="main-title">💼 Auditoria de Contratos (2025)</p>', unsafe_allow_html=True)
    st.markdown("Monitoramento de compras públicas e maiores fornecedores do Estado.")
    
    # Busca os dados (Lembre-se: o nome da tabela deve bater com o pgAdmin)
    try:
        df_contratos = carregar_dados("SELECT * FROM contratos_licitacoes WHERE ano_exercicio = 2025")
        
        if not df_contratos.empty:
            # Cards superiores
            col1, col2, col3 = st.columns(3)
            with col1:
                total_gasto = df_contratos['valor_contrato'].sum()
                st.markdown(f'<div class="metric-card"><p class="metric-label">Valor Total Contratado</p><p class="metric-value">R$ {total_gasto:,.2f}</p></div>', unsafe_allow_html=True)
            with col2:
                qtd_contratos = len(df_contratos)
                st.markdown(f'<div class="metric-card"><p class="metric-label">Qtd. de Contratos</p><p class="metric-value" style="color:#8A2BE2;">{qtd_contratos}</p></div>', unsafe_allow_html=True)
            with col3:
                ticket_medio = total_gasto / qtd_contratos if qtd_contratos > 0 else 0
                st.markdown(f'<div class="metric-card"><p class="metric-label">Ticket Médio (Por Contrato)</p><p class="metric-value" style="color:#00FA9A;">R$ {ticket_medio:,.2f}</p></div>', unsafe_allow_html=True)
            
            st.write("---")
            
            # Gráficos em Grid
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.subheader("🏆 Top 10 Maiores Fornecedores")
                top_fornecedores = df_contratos.groupby('nome_contratado')['valor_contrato'].sum().reset_index().sort_values(by='valor_contrato', ascending=False).head(10)
                # Removendo "NÃO INFORMADO" se for o maior
                top_fornecedores = top_fornecedores[top_fornecedores['nome_contratado'] != 'NÃO INFORMADO']
                
                fig1 = px.bar(top_fornecedores, x='valor_contrato', y='nome_contratado', orientation='h', 
                              color_discrete_sequence=['#00D4FF'], template='plotly_dark')
                fig1.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig1, use_container_width=True)

            with col_g2:
                st.subheader("📑 Gastos por Modalidade de Licitação")
                modalidade = df_contratos.groupby('modalidade_licitacao')['valor_contrato'].sum().reset_index()
                fig2 = px.pie(modalidade, values='valor_contrato', names='modalidade_licitacao', hole=0.6,
                              color_discrete_sequence=cores_neon, template='plotly_dark')
                fig2.update_layout(margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig2, use_container_width=True)

            # Tabela de Dados Brutos
            st.subheader("🔍 Investigador de Contratos")
            df_mostrar = df_contratos[['nome_orgao', 'nome_contratado', 'objeto_contrato', 'valor_contrato']].sort_values(by='valor_contrato', ascending=False)
            st.dataframe(df_mostrar.style.format({'valor_contrato': 'R$ {:,.2f}'}), use_container_width=True, height=300)

    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados: {e}. Verifique se a tabela 'contratos_licitacoes' existe e tem dados.")

# =====================================================================
# 6. TELA: DIÁRIAS E VIAGENS
# =====================================================================
elif aba_selecionada == "✈️ Diárias e Viagens":
    st.markdown('<p class="main-title">✈️ Diárias e Passagens</p>', unsafe_allow_html=True)
    st.write("Em construção... (Aqui entrarão os dados da tabela diarias_passagens)")

# =====================================================================
# 7. TELA: FOLHA DE PAGAMENTO
# =====================================================================
elif aba_selecionada == "👥 Folha de Pagamento":
    st.markdown('<p class="main-title">👥 Folha de Pagamento</p>', unsafe_allow_html=True)
    st.write("Em construção... (Aqui entrarão os dados da tabela folha_pagamento)")

# =====================================================================
# 8. TELA: VISÃO GERAL
# =====================================================================
else:
    st.markdown('<p class="main-title">👁️ Radar Goiano - Visão Geral</p>', unsafe_allow_html=True)
    st.markdown("### Bem-vindo ao Sistema de Auditoria Cidadã.")
    st.info("👈 Utilize o menu lateral para navegar entre os módulos financeiros do Estado de Goiás.")