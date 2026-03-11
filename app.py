import streamlit as st
from supabase import create_client

# Conexão
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="CRM Escrita Contabilidade", layout="wide")

# Estilo para botões e cards
st.markdown("""
    <style>
    .metric-card { background-color: #1a2a44; padding: 20px; border-radius: 10px; color: white; text-align: center; }
    div.stButton > button { border-radius: 5px; }
    .stTable { background-color: white; }
    </style>
    """, unsafe_allow_html=True)

def buscar_segmentos():
    try:
        res = supabase.table("segmentos").select("*").execute()
        return res.data
    except: return []

def buscar_perguntas():
    try:
        res = supabase.table("perguntas").select("*").execute()
        return res.data
    except: return []

st.sidebar.image("Logo Escrita.png", width=200)
menu = st.sidebar.selectbox("Navegação", ["Nova Proposta", "Configurações do Sistema"])

# --- CONFIGURAÇÕES ---
if menu == "Configurações do Sistema":
    st.title("⚙️ Gestão de Regras de Negócio")
    
    tab_segs, tab_pergs = st.tabs(["📂 Segmentos", "❓ Perguntas e Preços"])
    
    with tab_segs:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Novo Segmento")
            n_seg = st.text_input("Nome:")
            if st.button("Salvar Segmento"):
                supabase.table("segmentos").insert({"nome": n_seg}).execute()
                st.rerun()
        with col2:
            st.subheader("Lista de Segmentos")
            segs = buscar_segmentos()
            for s in segs:
                c_n, c_b = st.columns([3, 1])
                c_n.write(f"**{s['nome']}**")
                if c_b.button("Excluir", key=f"del_s_{s['id']}"):
                    supabase.table("segmentos").delete().eq("id", s['id']).execute()
                    st.rerun()

    with tab_pergs:
        st.subheader("Cadastrar Nova Regra")
        lista_s = [s['nome'] for s in buscar_segmentos()]
        
        with st.form("form_pergunta"):
            c1, c2 = st.columns(2)
            seg = c1.selectbox("Segmento", lista_s)
            tipo = c2.selectbox("Tipo de Dado", ["Número (Multiplicador)", "Múltipla Escolha (Valor Fixo)"])
            pergunta = st.text_input("Enunciado da Pergunta:")
            opcoes = st.text_input("Opções (se houver, separe por vírgula):")
            pesos = st.text_input("Valores R$ (separe por vírgula na mesma ordem):")
            
            if st.form_submit_button("Salvar Pergunta"):
                supabase.table("perguntas").insert({
                    "segmento": seg, "pergunta": pergunta, "opcoes": opcoes, 
                    "pesos_opcoes": pesos, "tipo_campo": tipo
                }).execute()
                st.success("Salvo!")
                st.rerun()
        
        st.divider()
        st.subheader("🔍 Perguntas Cadastradas")
        pergs = buscar_perguntas()
        if pergs:
            for p in pergs:
                with st.expander(f"{p['segmento']} - {p['pergunta']}"):
                    col_info, col_acao = st.columns([4, 1])
                    col_info.write(f"**Tipo:** {p['tipo_campo']}")
                    col_info.write(f"**Opções:** {p['opcoes'] if p['opcoes'] else 'N/A'}")
                    col_info.write(f"**Pesos:** {p['pesos_opcoes']}")
                    if col_acao.button("🗑️ Excluir", key=f"del_p_{p['id']}"):
                        supabase.table
