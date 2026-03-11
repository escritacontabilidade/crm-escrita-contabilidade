import streamlit as st

# Configuração da página com as cores da marca
st.set_page_config(page_title="CRM Escrita Contabilidade", layout="wide")

# Estilização para usar o Azul Marinho e Dourado (conforme o site)
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stButton>button { background-color: #1a2a44; color: white; border-radius: 5px; }
    .sidebar .sidebar-content { background-color: #1a2a44; }
    h1 { color: #1a2a44; }
    </style>
    """, unsafe_allow_html=True)

# Exibir a Logo que você subiu
st.image("Logo Escrita.png", width=250)

# Título Inicial
st.title("Sistema Comercial Inteligente")
st.subheader("Bem-vindo ao futuro da Escrita Contabilidade")

# Menu Lateral (Apenas o visual por enquanto)
st.sidebar.title("Menu Principal")
opcao = st.sidebar.selectbox("Navegar para:", ["Nova Proposta", "Painel Administrativo", "Indicadores"])

if opcao == "Nova Proposta":
    st.info("Aqui faremos o formulário mutável que você planejou!")
    segmento = st.selectbox("Selecione o Segmento:", ["Indústria", "Comércio", "Importadora", "Prestador de Serviço", "Clínicas Médicas", "Holding"])
    st.write(f"Você selecionou: **{segmento}**")

elif opcao == "Painel Administrativo":
    st.warning("Área Restrita: Aqui você mudará as perguntas e preços no futuro.")

elif opcao == "Indicadores":
    st.success("Área de Dashboards: Funil de vendas e Retenção.")
