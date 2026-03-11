import streamlit as st
from supabase import create_client

# Conexão
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="CRM Escrita Contabilidade", layout="wide")

# Estilos Visuais Corporativos
st.markdown("""
    <style>
    .metric-card { background-color: #1a2a44; padding: 20px; border-radius: 10px; color: white; text-align: center; }
    div.stButton > button { border-radius: 5px; width: 100%; }
    .btn-excluir > div > button { background-color: #ff4b4b !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# Funções de busca com tratamento de erro
def buscar_segmentos():
    res = supabase.table("segmentos").select("*").execute()
    return res.data

def buscar_perguntas():
    res = supabase.table("perguntas").select("*").execute()
    return res.data

st.sidebar.image("Logo Escrita.png", width=200)
menu = st.sidebar.selectbox("Navegação", ["Nova Proposta", "Configurações do Sistema"])

if menu == "Configurações do Sistema":
    st.title("⚙️ Gestão de Regras")
    t_seg, t_per = st.tabs(["📂 Segmentos", "❓ Perguntas"])

    with t_seg:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("Novo Segmento")
            n_seg = st.text_input("Nome do Segmento:")
            if st.button("Salvar"):
                supabase.table("segmentos").insert({"nome": n_seg}).execute()
                st.rerun()
        with c2:
            st.subheader("Lista de Segmentos")
            for s in buscar_segmentos():
                col_n, col_b = st.columns([3, 1])
                col_n.write(f"**{s['nome']}**")
                # CORREÇÃO AQUI: Comando de deleção explícito
                if col_b.button("Excluir", key=f"del_s_{s['id']}"):
                    supabase.from_("segmentos").delete().eq("id", s['id']).execute()
                    st.rerun()

    with t_per:
        st.subheader("Nova Pergunta")
        segs = buscar_segmentos()
        lista_nomes = [s['nome'] for s in segs]
        
        with st.form("cad_p"):
            c1, c2 = st.columns(2)
            f_seg = c1.selectbox("Segmento", lista_nomes)
            f_tipo = c2.selectbox("Tipo", ["Múltipla Escolha (Valor Fixo)", "Número (Multiplicador)"])
            f_perg = st.text_input("Pergunta:")
            f_opt = st.text_input("Opções (ex: Sim, Não)")
            f_pesos = st.text_input("Pesos R$ (ex: 100, 50)")
            if st.form_submit_button("Salvar Regra"):
                supabase.table("perguntas").insert({
                    "segmento": f_seg, "pergunta": f_perg, "tipo_campo": f_tipo,
                    "opcoes": f_opt, "pesos_opcoes": f_pesos
                }).execute()
                st.rerun()

        st.divider()
        st.subheader("Perguntas Ativas")
        for p in buscar_perguntas():
            with st.expander(f"{p['segmento']} - {p['pergunta']}"):
                c_inf, c_del = st.columns([4, 1])
                c_inf.write(f"Pesos: {p['pesos_opcoes']}")
                # CORREÇÃO AQUI: Comando de deleção explícito
                if c_del.button("🗑️ Deletar", key=f"del_p_{p['id']}"):
                    supabase.from_("perguntas").delete().eq("id", p['id']).execute()
                    st.rerun()

elif menu == "Nova Proposta":
    st.title("📄 Simulador de Honorários")
    segs = buscar_segmentos()
    lista_s = [s['nome'] for s in segs]
    if lista_s:
        seg_sel = st.selectbox("Selecione o segmento:", lista_s)
        perguntas = supabase.table("perguntas").select("*").eq("segmento", seg_sel).execute().data
        
        total = 0.0
        if perguntas:
            for p in perguntas:
                if "Múltipla Escolha" in p['tipo_campo']:
                    ops = [o.strip() for o in p['opcoes'].split(",")]
                    vls = [float(v.strip()) for v in p['pesos_opcoes'].split(",")]
                    esc = st.selectbox(p['pergunta'], ops, key=f"run_{p['id']}")
                    total += vls[ops.index(esc)]
                else:
                    n_in = st.number_input(p['pergunta'], min_value=0, key=f"run_{p['id']}")
                    total += (n_in * float(p['pesos_opcoes']))
            
            st.markdown(f'<div class="metric-card"><p>Honorário Mensal</p><h2>R$ {total:,.2f}</h2></div>', unsafe_allow_html=True)
