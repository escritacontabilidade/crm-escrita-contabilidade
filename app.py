import streamlit as st
from supabase import create_client

# 1. Conexão com o seu Banco de Dados (Supabase)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# 2. Configuração Visual (Estilo Sério e Profissional)
st.set_page_config(page_title="Escrita Contabilidade - CRM", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #f4f4f4; }
    .sidebar .sidebar-content { background-color: #1a2a44; color: white; }
    h1, h2, h3 { color: #1a2a44; }
    div.stButton > button { background-color: #1a2a44; color: #ffffff; border-radius: 4px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 3. Logo e Menu Lateral
st.sidebar.image("Logo Escrita.png", width=200)
menu = st.sidebar.selectbox("Menu Principal", ["Nova Proposta", "Painel Administrativo", "Indicadores"])

# --- ÁREA ADMINISTRATIVA (Onde você cria as perguntas) ---
if menu == "Painel Administrativo":
    st.title("⚙️ Gestão de Formulários")
    st.subheader("Configure as perguntas do sistema aqui")
    
    with st.form("cadastrar_pergunta"):
        segmento = st.selectbox("Segmento", ["Indústria", "Comércio", "Importadora", "Prestador de Serviço", "Clínicas Médicas", "Holding"])
        enunciado = st.text_input("Escreva a pergunta que o cliente verá:")
        tipo = st.selectbox("Tipo de Resposta", ["Número", "Texto", "Sim/Não"])
        peso = st.number_input("Peso/Impacto no Preço (R$)", min_value=0.0)
        
        btn_salvar = st.form_submit_button("Salvar Pergunta no Sistema")
        
        if btn_salvar:
            # Comando para salvar no Supabase
            dados = {"segmento": segmento, "pergunta": enunciado, "peso": peso}
            supabase.table("perguntas").insert(dados).execute()
            st.success(f"Pergunta para {segmento} salva com sucesso!")

# --- ÁREA DE VENDAS (Onde o formulário aparece) ---
elif menu == "Nova Proposta":
    st.title("📄 Nova Proposta Comercial")
    seg_escolhido = st.selectbox("Selecione o segmento do cliente:", ["Indústria", "Comércio", "Importadora", "Prestador de Serviço", "Clínicas Médicas", "Holding"])
    
    # Busca no banco apenas as perguntas do segmento selecionado
    res = supabase.table("perguntas").select("*").eq("segmento", seg_escolhido).execute()
    perguntas_do_banco = res.data
    
    if perguntas_do_banco:
        st.write("### Preencha os dados abaixo:")
        for p in perguntas_do_banco:
            st.number_input(p['pergunta'], key=p['id'])
        st.button("Gerar Orçamento e Proposta")
    else:
        st.info("Ainda não há perguntas cadastradas para este segmento. Vá ao Painel Administrativo.")
