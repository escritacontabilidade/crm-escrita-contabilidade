import streamlit as st
from supabase import create_client

# Conexão Segura
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Design Corporativo
st.set_page_config(page_title="CRM Escrita Contabilidade", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    h1, h2, h3 { color: #1a2a44; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stSelectbox, .stNumberInput { margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

def buscar_segmentos():
    return [s['nome'] for s in supabase.table("segmentos").select("nome").execute().data]

st.sidebar.image("Logo Escrita.png", width=200)
menu = st.sidebar.selectbox("Navegação", ["Nova Proposta", "Configurações do Sistema"])

if menu == "Configurações do Sistema":
    st.title("⚙️ Configuração de Questionários")
    t1, t2 = st.tabs(["Cadastrar Segmentos", "Cadastrar Perguntas"])
    
    with t1:
        nome_seg = st.text_input("Novo Segmento (Ex: Clínica Médica):")
        if st.button("Adicionar Segmento"):
            supabase.table("segmentos").insert({"nome": nome_seg}).execute()
            st.rerun()
            
    with t2:
        lista_s = buscar_segmentos()
        with st.form("cad_pergunta"):
            seg = st.selectbox("Segmento", lista_s)
            texto = st.text_input("Pergunta (Enunciado):")
            tipo = st.selectbox("Tipo de Resposta", ["Número", "Múltipla Escolha"])
            opcoes = st.text_input("Se for Múltipla Escolha, digite as opções separadas por vírgula (ex: Simples, Real, Presumido):")
            peso = st.number_input("Valor de acréscimo no honorário (R$):")
            if st.form_submit_button("Salvar Pergunta"):
                supabase.table("perguntas").insert({
                    "segmento": seg, "pergunta": texto, "peso": peso, "opcoes": opcoes
                }).execute()
                st.success("Salvo com sucesso!")

elif menu == "Nova Proposta":
    st.title("📄 Elaboração de Proposta")
    lista_s = buscar_segmentos()
    if lista_s:
        cliente = st.text_input("Nome do Prospecto / Empresa:")
        seg_sel = st.selectbox("Segmento do Cliente:", lista_s)
        
        st.divider()
        
        # Busca perguntas do banco
        perguntas = supabase.table("perguntas").select("*").eq("segmento", seg_sel).execute().data
        
        respostas = {}
        total_honorario = 0.0 # Aqui começaria sua base de preço (ex: 500.0)

        if perguntas:
            for p in perguntas:
                if p['opcoes']: # Se tiver opções, vira um Selectbox
                    lista_ops = [opt.strip() for opt in p['opcoes'].split(",")]
                    respostas[p['pergunta']] = st.selectbox(p['pergunta'], lista_ops)
                else: # Se não, vira um campo de número
                    respostas[p['pergunta']] = st.number_input(p['pergunta'], min_value=0)
                
                # Lógica básica de soma (podemos refinar depois)
                total_honorario += float(p['peso'])

            if st.button("Gerar Orçamento"):
                st.success(f"### Proposta para: {cliente}")
                st.metric("Honorário Estimado", f"R$ {total_honorario:,.2f}")
                st.write("Dados processados com base no questionário técnico.")
        else:
            st.info("Cadastre as perguntas para este segmento nas Configurações.")
