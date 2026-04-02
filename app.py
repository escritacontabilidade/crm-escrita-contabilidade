import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
import datetime
import os

# --- 1. CONFIGURAÇÃO DA PÁGINA (DESIGN CRM) ---
st.set_page_config(page_title="CRM & Precificação Escrita", layout="wide", page_icon="📄")

# --- 2. CONEXÕES (SUPABASE + GOOGLE SHEETS) ---
# Conexão CRM (Supabase)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Conexão Planilha (Google Sheets)
conn = st.connection("gsheets", type=GSheetsConnection)

# Nomes exatos das abas das suas imagens
ABA_CUSTOS = "Custos"
ABA_PESOS = "Pesos"
ABA_ORCAMENTOS = "Orcamentos"

# --- 3. ESTILOS VISUAIS ---
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
        self.set_font("Arial", 'B', 18)
        self.set_text_color(26, 42, 68)
        self.cell(140, 10, "PROPOSTA COMERCIAL", 0, 1, 'R')
        self.ln(15)

    def footer(self):
        self.set_y(-20)
        self.set_font("Arial", 'I', 8)
        self.cell(0, 10, f"Escrita Contabilidade | Pagina {self.page_no()}", 0, 0, 'C')

def gerar_pdf(dados, total):
    pdf = PDFProposta()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"CLIENTE: {dados['nome'].upper()}", ln=True)
    pdf.ln(10)
    pdf.set_fill_color(26, 42, 68)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(130, 12, "  Descricao", 0, 0, 'L', True)
    pdf.cell(60, 12, "Valor Mensal  ", 0, 1, 'R', True)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(130, 15, "  Honorarios Contabeis", 'B')
    pdf.cell(60, 15, f"{formatar_moeda(total)}  ", 'B', 1, 'R')
    return pdf.output()

# --- 5. MENU LATERAL ---
st.sidebar.image("Logo Escrita.png", width=200)
menu = st.sidebar.selectbox("Navegação", ["Nova Proposta (CRM)", "Custos da Operação (Planilha)", "Histórico de Vendas", "Configurações Supabase"])

# --- MÓDULO 1: NOVA PROPOSTA (Lógica CRM + Salvar Planilha) ---
if menu == "Nova Proposta (CRM)":
    st.title("📄 Elaboração de Proposta Comercial")
    
    # Busca segmentos do Supabase
    segs = supabase.table("segmentos").select("*").execute().data
    lista_s = [s['nome'] for s in segs]
    
    if lista_s:
        c1, c2 = st.columns([2, 1])
        with c1:
            nome_cliente = st.text_input("Nome da Empresa / Prospecto:")
        with c2:
            seg_sel = st.selectbox("Selecione o segmento:", lista_s)
        
        st.divider()
        
        # Busca perguntas dinâmicas do Supabase
        perguntas = supabase.table("perguntas").select("*").eq("segmento", seg_sel).execute().data
        total_proposta = 0.0

        if perguntas:
            st.subheader("📋 Questionário de Diagnóstico")
            for p in perguntas:
                if "Múltipla Escolha" in p['tipo_campo']:
                    ops = [o.strip() for o in p['opcoes'].split(",")]
                    vls = [float(v.strip()) for v in p['pesos_opcoes'].split(",")]
                    esc = st.selectbox(p['pergunta'], ops, key=f"p_{p['id']}")
                    total_proposta += vls[ops.index(esc)]
                else:
                    n_in = st.number_input(p['pergunta'], min_value=0, key=f"p_{p['id']}")
                    total_proposta += (n_in * float(p['pesos_opcoes']))
            
            st.markdown(f'<div class="metric-card"><p>Honorário Estimado</p><h2>{formatar_moeda(total_proposta)}</h2></div>', unsafe_allow_html=True)
            
            if nome_cliente and st.button("💾 Gerar PDF e Salvar na Planilha"):
                # Geração PDF
                pdf_bytes = gerar_pdf({"nome": nome_cliente, "segmento": seg_sel}, total_proposta)
                st.download_button("📥 Baixar Proposta PDF", data=bytes(pdf_bytes), file_name=f"Proposta_{nome_cliente}.pdf")
                
                # Salvar no Google Sheets (Aba Orcamentos)
                try:
                    df_vendas = conn.read(worksheet=ABA_ORCAMENTOS, ttl=0)
                    nova_venda = pd.DataFrame([[nome_cliente, datetime.date.today().strftime('%d/%m/%Y'), total_proposta, seg_sel]], columns=df_vendas.columns)
                    df_final = pd.concat([df_vendas, nova_venda], ignore_index=True)
                    conn.update(worksheet=ABA_ORCAMENTOS, data=df_final)
                    st.success("✅ Orçamento salvo na Planilha!")
                except Exception as e: st.error(f"Erro ao salvar na planilha: {e}")

# --- MÓDULO 2: CUSTOS (Leitura da Planilha) ---
elif menu == "Custos da Operação (Planilha)":
    st.title("💰 Configuração de Custos (Planilha)")
    try:
        df_custos = conn.read(worksheet=ABA_CUSTOS, ttl=0)
        st.write("Dados atuais da aba 'Custos':")
        st.dataframe(df_custos)
        
        # Lógica de Custo Hora (da planilha)
        pessoal = float(df_custos.iloc[0, 1])
        gerais = float(df_custos.iloc[1, 1])
        colab = int(df_custos.iloc[4, 1])
        horas = float(df_custos.iloc[3, 1])
        
        custo_hora = (pessoal + gerais) / (colab * horas) if colab > 0 else 0
        st.metric("Custo Hora Calculado (Planilha)", formatar_moeda(custo_hora))
    except: st.error("Erro ao ler aba 'Custos'. Verifique o nome na planilha.")

# --- MÓDULO 3: HISTÓRICO ---
elif menu == "Histórico de Vendas":
    st.title("📊 Histórico de Orçamentos Gerados")
    df_h = conn.read(worksheet=ABA_ORCAMENTOS, ttl=0)
    st.dataframe(df_h, use_container_width=True)

# --- MÓDULO 4: CONFIGURAÇÕES SUPABASE ---
elif menu == "Configurações Supabase":
    st.title("⚙️ Gestão de Segmentos e Regras")
    # Mantém todas as funções de inserir segmentos e perguntas que você já tinha
    n_seg = st.text_input("Novo Segmento:")
    if st.button("Salvar Segmento"):
        supabase.table("segmentos").insert({"nome": n_seg}).execute()
        st.rerun()
