import streamlit as st
import pandas as pd
from supabase import create_client
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
import datetime
import os

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema Integrado Escrita Contabilidade", layout="wide", page_icon="📄")

# --- 2. CONEXÕES (SUPABASE + GOOGLE SHEETS) ---
# Supabase (Dados do CRM)
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Erro na conexão com Supabase. Verifique se a restauração do projeto terminou.")

# Google Sheets (Dados de Custos e Pesos)
conn = st.connection("gsheets", type=GSheetsConnection)

# IDs exatos das abas conforme sua imagem (Custos, Pesos, Orcamentos)
# No Streamlit GSheets, usamos o nome da aba para facilitar
NOME_ABA_CUSTOS = "Custos"
NOME_ABA_PESOS = "Pesos"
NOME_ABA_ORCAMENTOS = "Orcamentos"

# --- 3. ESTILOS CSS ---
st.markdown("""
    <style>
    .metric-card { 
        background-color: #1a2a44; padding: 30px; border-radius: 15px; 
        color: white; text-align: center; border: 2px solid #d4af37;
    }
    .metric-card h2 { color: #d4af37 !important; font-size: 3rem !important; margin: 15px 0 !important; }
    div.stButton > button { border-radius: 5px; font-weight: bold; width: 100%; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNÇÕES DO CRM (SUPABASE) ---
def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def buscar_segmentos():
    try:
        res = supabase.table("segmentos").select("*").execute()
        return res.data
    except: return []

def buscar_perguntas(segmento=None):
    try:
        query = supabase.table("perguntas").select("*")
        if segmento:
            query = query.eq("segmento", segmento)
        res = query.execute()
        return res.data
    except: return []

# --- 5. CLASSE DO PDF (DESIGN CRM) ---
class PDFProposta(FPDF):
    def header(self):
        self.set_fill_color(26, 42, 68)
        self.rect(0, 0, 5, 297, 'F')
        if os.path.exists("Logo Escrita.png"):
            self.image("Logo Escrita.png", 10, 10, 40)
        self.set_xy(60, 15)
        self.set_font("Arial", 'B', 18)
        self.set_text_color(26, 42, 68)
        self.cell(140, 10, "PROPOSTA COMERCIAL", 0, 1, 'R')
        self.ln(15)

    def footer(self):
        self.set_y(-20)
        self.set_font("Arial", 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Escrita Contabilidade | Pagina {self.page_no()}", 0, 0, 'C')

def gerar_pdf(dados, total):
    pdf = PDFProposta()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"CLIENTE: {dados['nome'].upper()}", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Segmento: {dados['segmento']}", ln=True)
    pdf.ln(10)
    pdf.set_fill_color(26, 42, 68)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(130, 12, "  Descricao", 0, 0, 'L', True)
    pdf.cell(60, 12, "Valor Mensal  ", 0, 1, 'R', True)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(130, 15, "  Honorarios Contabeis", 'B')
    pdf.cell(60, 15, f"{formatar_moeda(total)}  ", 'B', 1, 'R')
    return pdf.output()

# --- 6. INTERFACE DE NAVEGAÇÃO ---
st.sidebar.image("Logo Escrita.png", width=200)
menu = st.sidebar.selectbox("Navegação", ["Nova Proposta", "Histórico de Orçamentos", "Configurar CRM", "Custos Operacionais"])

# --- ABA 1: NOVA PROPOSTA ---
if menu == "Nova Proposta":
    st.title("📄 Gerador de Propostas")
    segs = buscar_segmentos()
    lista_s = [s['nome'] for s in segs]
    
    if lista_s:
        nome_cliente = st.text_input("Nome do Prospecto")
        seg_sel = st.selectbox("Segmento", lista_s)
        
        perguntas = buscar_perguntas(seg_sel)
        total = 0.0
        
        if perguntas:
            for p in perguntas:
                if "Múltipla Escolha" in p['tipo_campo']:
                    ops = [o.strip() for o in p['opcoes'].split(",")]
                    vls = [float(v.strip()) for v in p['pesos_opcoes'].split(",")]
                    esc = st.selectbox(p['pergunta'], ops, key=f"p_{p['id']}")
                    total += vls[ops.index(esc)]
                else:
                    n_in = st.number_input(p['pergunta'], min_value=0, key=f"p_{p['id']}")
                    total += (n_in * float(p['pesos_opcoes']))
            
            st.markdown(f'<div class="metric-card"><p>Honorário Sugerido</p><h2>{formatar_moeda(total)}</h2></div>', unsafe_allow_html=True)
            
            if nome_cliente and st.button("Gerar PDF e Salvar"):
                pdf_bytes = gerar_pdf({"nome": nome_cliente, "segmento": seg_sel}, total)
                st.download_button("📥 Baixar PDF", data=bytes(pdf_bytes), file_name=f"Proposta_{nome_cliente}.pdf")
                
                # Salva na Planilha Google
                df_h = conn.read(worksheet=NOME_ABA_ORCAMENTOS, ttl=0)
                nova_linha = pd.DataFrame([[nome_cliente, datetime.date.today().strftime('%d/%m/%Y'), total, seg_sel]], columns=df_h.columns)
                conn.update(worksheet=NOME_ABA_ORCAMENTOS, data=pd.concat([df_h, nova_linha]))
                st.success("Orçamento registrado na planilha!")
    else:
        st.warning("Aguardando o Supabase restaurar os dados ou cadastre um segmento.")

# --- ABA 2: HISTÓRICO (GOOGLE SHEETS) ---
elif menu == "Histórico de Orçamentos":
    st.title("📊 Histórico Gravado na Planilha")
    df_h = conn.read(worksheet=NOME_ABA_ORCAMENTOS, ttl=0)
    st.dataframe(df_h, use_container_width=True)

# --- ABA 3: CONFIGURAR CRM (SUPABASE) ---
elif menu == "Configurar CRM":
    st.title("⚙️ Gerenciar Segmentos e Perguntas")
    tab1, tab2 = st.tabs(["Segmentos", "Perguntas"])
    with tab1:
        n_seg = st.text_input("Novo Segmento")
        if st.button("Adicionar"):
            supabase.table("segmentos").insert({"nome": n_seg}).execute()
            st.rerun()
    with tab2:
        st.write("Configure aqui os pesos de cada pergunta para o cálculo automático.")

# --- ABA 4: CUSTOS (GOOGLE SHEETS) ---
elif menu == "Custos Operacionais":
    st.title("💰 Custos da Operação")
    df_c = conn.read(worksheet=NOME_ABA_CUSTOS, ttl=0)
    st.write("Dados extraídos da aba 'Custos':")
    st.table(df_c)
