import streamlit as st
from supabase import create_client

# 1. Conexão
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# 2. Configuração Visual Séria
st.set_page_config(page_title="Escrita Contabilidade - CRM", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #f4f4f4; }
    h1, h2, h3 { color: #1a2a44; }
    div.stButton > button { background-color: #1a2a44; color: #ffffff; }
    </style>
    """, unsafe_allow_html=True)

# 3. Funções para buscar dados vivos do Banco
def buscar_segmentos():
    res = supabase.table("segmentos").select("nome").execute()
    return [item['nome'] for item in res.data]

# 4. Logo e Menu
st.sidebar.image("Logo Escrita.png", width=200)
menu = st.sidebar.selectbox("Menu Principal", ["Nova Proposta", "Painel Administrativo"])

# --- PAINEL ADMINISTRATIVO ---
if menu == "Painel Administrativo":
    st.title("⚙️ Gestão Estratégica")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Cadastrar Novo Segmento")
        novo_seg = st.text_input("Nome do Segmento (ex: Holding):")
        if st.button("Salvar Segmento"):
            supabase.table("segmentos").insert({"nome": novo_seg}).execute()
            st.success("Segmento adicionado!")
            st.rerun()

    with col2:
        st.subheader("Cadastrar Pergunta")
        # Aqui o sistema busca os segmentos que já existem no banco!
        lista_segs = buscar_segmentos()
        seg_alvo = st.selectbox("Para qual segmento?", lista_segs)
        pergunta_texto = st.text_input("Pergunta:")
        peso_valor = st.number_input("Peso no Preço (R$):", min_value=0.0)
        
        if st.button("Salvar Pergunta"):
            supabase.table("perguntas").insert({
                "segmento": seg_alvo, 
                "pergunta": pergunta_texto, 
                "peso": peso_valor
            }).execute()
            st.success("Pergunta salva!")

# --- NOVA PROPOSTA ---
elif menu == "Nova Proposta":
    st.title("📄 Nova Proposta Comercial")
    lista_segs = buscar_segmentos()
    seg_escolhido = st.selectbox("Selecione o segmento do cliente:", lista_segs)
    
    res = supabase.table("perguntas").select("*").eq("segmento", seg_escolhido).execute()
    
    if res.data:
        st.write("### Diagnóstico do Cliente")
        for p in res.data:
            st.number_input(p['pergunta'], key=str(p['id']))
        st.button("Calcular Proposta")
    else:
        st.info("Nenhuma pergunta configurada para este segmento.")
