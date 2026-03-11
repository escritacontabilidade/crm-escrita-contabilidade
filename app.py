import streamlit as st
from supabase import create_client

# Conexão
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="CRM Escrita Contabilidade", layout="wide")

# Estilo para um Dashboard Profissional
st.markdown("""
    <style>
    .metric-card { background-color: #1a2a44; padding: 20px; border-radius: 10px; color: white; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

def buscar_segmentos():
    return [s['nome'] for s in supabase.table("segmentos").select("nome").execute().data]

st.sidebar.image("Logo Escrita.png", width=200)
menu = st.sidebar.selectbox("Navegação", ["Nova Proposta", "Configurações do Sistema"])

if menu == "Configurações do Sistema":
    st.title("⚙️ Configuração de Preços e Regras")
    t1, t2 = st.tabs(["Segmentos", "Perguntas e Preços"])
    
    with t1:
        nome_seg = st.text_input("Novo Segmento:")
        if st.button("Adicionar"):
            supabase.table("segmentos").insert({"nome": nome_seg}).execute()
            st.rerun()
            
    with t2:
        lista_s = buscar_segmentos()
        with st.form("cad_pergunta"):
            seg = st.selectbox("Segmento", lista_s)
            texto = st.text_input("Pergunta:")
            tipo = st.selectbox("Tipo", ["Número (Multiplicador)", "Múltipla Escolha (Valor Fixo)"])
            opcoes = st.text_input("Opções (separadas por vírgula):", help="Ex: Simples, Presumido, Real")
            pesos = st.text_input("Valores/Pesos correspondentes (separados por vírgula):", help="Ex: 100, 300, 800")
            
            if st.form_submit_button("Salvar Regra"):
                supabase.table("perguntas").insert({
                    "segmento": seg, "pergunta": texto, "opcoes": opcoes, "pesos_opcoes": pesos, "tipo_campo": tipo
                }).execute()
                st.success("Regra de preço salva!")

elif menu == "Nova Proposta":
    st.title("📄 Simulador de Honorários")
    lista_s = buscar_segmentos()
    
    if lista_s:
        col_cli, col_seg = st.columns(2)
        cliente = col_cli.text_input("Nome da Empresa:")
        seg_sel = col_seg.selectbox("Segmento:", lista_s)
        
        st.divider()
        perguntas = supabase.table("perguntas").select("*").eq("segmento", seg_sel).execute().data
        
        total_honorario = 0.0
        
        if perguntas:
            for p in perguntas:
                # Lógica para Múltipla Escolha
                if "Múltipla Escolha" in p['tipo_campo']:
                    lista_ops = [o.strip() for o in p['opcoes'].split(",")]
                    lista_pesos = [float(val.strip()) for val in p['pesos_opcoes'].split(",")]
                    
                    escolha = st.selectbox(p['pergunta'], lista_ops)
                    
                    # Acha o índice da escolha para pegar o peso certo
                    idx = lista_ops.index(escolha)
                    total_honorario += lista_pesos[idx]
                
                # Lógica para Números (Multiplicador)
                else:
                    valor_input = st.number_input(p['pergunta'], min_value=0)
                    peso_unitario = float(p['pesos_opcoes'])
                    total_honorario += (valor_input * peso_unitario)

            st.divider()
            st.markdown(f"""
                <div class="metric-card">
                    <p style="margin:0; font-size: 1.2rem;">Honorário Mensal Estimado</p>
                    <h2 style="margin:0; font-size: 3rem; color: #d4af37;">R$ {total_honorario:,.2f}</h2>
                    <p style="margin:0; opacity: 0.8;">Cliente: {cliente}</p>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("Salvar Proposta no Histórico"):
                st.info("Funcionalidade em desenvolvimento...")
