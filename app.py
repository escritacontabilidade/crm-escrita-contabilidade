import streamlit as st
import pandas as pd
from supabase import create_client
from fpdf import FPDF
import datetime
import os

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="CRM & Precificação Escrita", layout="wide", page_icon="📄")

# --- 2. CONEXÃO ÚNICA (SUPABASE) ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"Erro de conexão com o Supabase: {e}")

# --- 3. ESTILOS VISUAIS ---
st.markdown("""
    <style>
    .metric-card { 
        background-color: #1a2a44; padding: 25px; border-radius: 12px; 
        color: white; text-align: center; border: 1px solid #d4af37;
    }
    .metric-card h2 { color: #d4af37 !important; margin: 10px 0 !important; }
    div.stButton > button { border-radius: 5px; font-weight: bold; width: 100%; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNÇÕES DE SUPORTE (FORMATAÇÃO E PDF) ---
def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

class PDFProposta(FPDF):
    def header(self):
        self.set_fill_color(26, 42, 68)
        self.rect(0, 0, 5, 297, 'F')
        if os.path.exists("Logo Escrita.png"):
            self.image("Logo Escrita.png", 10, 10, 40)
        self.set_xy(60, 15)
        self.set_font("Arial", 'B', 16)
        self.set_text_color(26, 42, 68)
        self.cell(140, 10, "PROPOSTA COMERCIAL", 0, 1, 'R')
        self.ln(15)

    def footer(self):
        self.set_y(-20)
        self.set_font("Arial", 'I', 8)
        self.cell(0, 10, f"Escrita Contabilidade | Pagina {self.page_no()}", 0, 0, 'C')

def gerar_pdf(dados, mensal, extras_df):
    pdf = PDFProposta()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"CLIENTE: {dados['nome'].upper()}", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Segmento: {dados['segmento']}", ln=True)
    pdf.ln(10)
    
    # Mensal
    pdf.set_fill_color(26, 42, 68); pdf.set_text_color(255, 255, 255)
    pdf.cell(130, 10, "  Servico Recorrente", 1, 0, 'L', True)
    pdf.cell(60, 10, "Valor Mensal", 1, 1, 'C', True)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(130, 10, "  Honorarios Contabeis", 1)
    pdf.cell(60, 10, f"  {formatar_moeda(mensal)}", 1, 1, 'R')
    
    # Avulsos
    if not extras_df.empty:
        pdf.ln(5)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(130, 10, "  Servicos Extras / Avulsos", 1, 0, 'L', True)
        pdf.cell(60, 10, "Valor Unico", 1, 1, 'C', True)
        for _, row in extras_df.iterrows():
            pdf.cell(130, 10, f"  {row['servico']}", 1)
            pdf.cell(60, 10, f"  {formatar_moeda(row['valor'])}", 1, 1, 'R')
            
    return pdf.output()

# --- 5. MENU LATERAL ---
if os.path.exists("Logo Escrita.png"):
    st.sidebar.image("Logo Escrita.png", width=200)
menu = st.sidebar.selectbox("Navegação", ["Nova Proposta", "Dashboard de Custos", "Histórico de Vendas", "Configurações"])

# --- MÓDULO 1: NOVA PROPOSTA ---
if menu == "Nova Proposta":
    st.title("📄 Elaboração de Proposta")
    
    # Carregar Segmentos do Supabase
    res_seg = supabase.table("segmentos").select("*").execute()
    lista_s = [s['nome'] for s in res_seg.data] if res_seg.data else []

    if lista_s:
        c1, c2 = st.columns([2, 1])
        nome_cliente = c1.text_input("Nome da Empresa:")
        seg_sel = c2.selectbox("Segmento:", lista_s)
        
        st.divider()
        
        # 1. Honorário Mensal (Perguntas)
        total_mensal = 0.0
        res_perg = supabase.table("perguntas").select("*").eq("segmento", seg_sel).execute()
        if res_perg.data:
            st.subheader("📋 Diagnóstico Mensal")
            for p in res_perg.data:
                if "Múltipla Escolha" in p['tipo_campo']:
                    ops = [o.strip() for o in p['opcoes'].split(",")]
                    vls = [float(v.strip()) for v in p['pesos_opcoes'].split(",")]
                    esc = st.selectbox(p['pergunta'], ops, key=f"p_{p['id']}")
                    total_mensal += vls[ops.index(esc)]
                else:
                    n_in = st.number_input(p['pergunta'], min_value=0, key=f"p_{p['id']}")
                    total_mensal += (n_in * float(p['pesos_opcoes']))

        # 2. Serviços Avulsos (Busca da tabela servicos_avulsos)
        st.subheader("➕ Serviços Avulsos / Retrabalhos")
        res_av = supabase.table("servicos_avulsos").select("*").execute()
        if res_av.data:
            df_av = pd.DataFrame(res_av.data)
            selecionados = st.multiselect("Selecione os serviços extras:", df_av['servico'].tolist())
            df_sel = df_av[df_av['servico'].isin(selecionados)]
            total_extras = df_sel['valor'].sum()
        else:
            total_extras = 0.0
            df_sel = pd.DataFrame()

        # Resumo Visual
        total_geral = total_mensal + total_extras
        st.markdown(f"""
            <div class="metric-card">
                <p>Mensal: {formatar_moeda(total_mensal)} | Extras: {formatar_moeda(total_extras)}</p>
                <h2>Total Proposta: {formatar_moeda(total_geral)}</h2>
            </div>
        """, unsafe_allow_html=True)

        if nome_cliente and st.button("💾 Finalizar Proposta"):
            # Salva no Histórico
            supabase.table("historico_vendas").insert({
                "cliente": nome_cliente,
                "segmento": seg_sel,
                "valor_total": total_geral
            }).execute()
            
            # Gera PDF
            pdf_bytes = gerar_pdf({"nome": nome_cliente, "segmento": seg_sel}, total_mensal, df_sel)
            st.download_button("📥 Baixar PDF", data=bytes(pdf_bytes), file_name=f"Proposta_{nome_cliente}.pdf")
            st.success("Proposta salva no histórico!")

# --- MÓDULO 2: CUSTOS ---
elif menu == "Dashboard de Custos":
    st.title("💰 Custos Fixos da Operação")
    res_c = supabase.table("custos_fixos").select("*").execute()
    if res_c.data:
        df_c = pd.DataFrame(res_c.data)
        st.table(df_c[['item', 'valor']])
        st.metric("Custo Total Mensal", formatar_moeda(df_c['valor'].sum()))
    else:
        st.info("Nenhum custo cadastrado.")

# --- MÓDULO 3: HISTÓRICO ---
elif menu == "Histórico de Vendas":
    st.title("📊 Histórico de Orçamentos")
    res_h = supabase.table("historico_vendas").select("*").order("data_criacao", desc=True).execute()
    if res_h.data:
        st.dataframe(pd.DataFrame(res_h.data), use_container_width=True)
    else:
        st.info("Nenhum histórico encontrado.")

# --- MÓDULO 4: CONFIGURAÇÕES ---
elif menu == "Configurações":
    st.title("⚙️ Painel Administrativo")
    tab1, tab2, tab3 = st.tabs(["Segmentos/Regras", "Preços Avulsos", "Custos Fixos"])
    
    with tab1:
        st.subheader("Gerenciar Segmentos")
        # (Aqui você mantém aquela lógica de cadastrar segmentos e perguntas que já tínhamos)
        
    with tab2:
        st.subheader("Cadastrar Preço de Serviço Avulso")
        with st.form("form_avulso"):
            n_serv = st.text_input("Nome do Serviço (ex: Alteração de Contrato)")
            n_val = st.number_input("Valor (R$)", min_value=0.0)
            n_cat = st.selectbox("Categoria", ["Fiscal", "DP", "Contábil", "Legalização"])
            if st.form_submit_button("Salvar Serviço"):
                supabase.table("servicos_avulsos").insert({"servico": n_serv, "valor": n_val, "categoria": n_cat}).execute()
                st.rerun()

    with tab3:
        st.subheader("Cadastrar Custo Fixo")
        with st.form("form_custo"):
            n_item = st.text_input("Item de Custo")
            n_v_custo = st.number_input("Valor Mensal", min_value=0.0)
            if st.form_submit_button("Salvar Custo"):
                supabase.table("custos_fixos").insert({"item": n_item, "valor": n_v_custo}).execute()
                st.rerun()
