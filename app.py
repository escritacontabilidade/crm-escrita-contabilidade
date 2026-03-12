import streamlit as st
from supabase import create_client
from fpdf import FPDF
import datetime
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="CRM Escrita Contabilidade", layout="wide", page_icon="📄")

# --- CONEXÃO SUPABASE ---
# Certifique-se de que estas chaves estão configuradas no seu arquivo secrets.toml ou no painel do Streamlit Cloud
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- ESTILOS CSS (Interface Streamlit) ---
st.markdown("""
    <style>
    .metric-card { 
        background-color: #1a2a44; 
        padding: 30px; 
        border-radius: 15px; 
        color: white; 
        text-align: center;
        border: 2px solid #d4af37;
    }
    .metric-card h2 { color: #d4af37 !important; font-size: 3rem !important; margin: 10px 0 !important; }
    div.stButton > button { border-radius: 5px; font-weight: bold; }
    .stTabs [data-baseweb="tab"] { font-size: 1.1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES AUXILIARES ---
def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def buscar_segmentos():
    res = supabase.table("segmentos").select("*").execute()
    return res.data

def buscar_perguntas():
    res = supabase.table("perguntas").select("*").execute()
    return res.data

# --- GERADOR DE PDF (Design Aprimorado) ---
class PDFProposta(FPDF):
    def header(self):
        # Tarja lateral decorativa Azul Escuro
        self.set_fill_color(26, 42, 68) 
        self.rect(0, 0, 5, 297, 'F')
        
        # Logo - Verifica se o arquivo existe para não quebrar o código
        logo_path = "Logo Escrita.png"
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 8, 45)
        else:
            # Fallback caso a logo suma: Nome da empresa em texto
            self.set_font("Arial", 'B', 15)
            self.set_text_color(26, 42, 68)
            self.set_xy(10, 10)
            self.cell(0, 10, "ESCRITA CONTABILIDADE")

        # Título à direita
        self.set_xy(60, 12)
        self.set_font("Arial", 'B', 18)
        self.set_text_color(26, 42, 68)
        self.cell(140, 10, "PROPOSTA COMERCIAL", 0, 1, 'R')
        
        self.set_xy(60, 20)
        self.set_font("Arial", '', 10)
        self.set_text_color(100, 100, 100)
        self.cell(140, 5, "Inteligencia Contabil e Gestao Estrategica", 0, 1, 'R')
        
        # Linha decorativa horizontal (Dourada)
        self.set_draw_color(212, 175, 55)
        self.line(10, 38, 200, 38)
        self.ln(25)

    def footer(self):
        self.set_y(-20)
        self.set_font("Arial", 'I', 8)
        self.set_text_color(150, 150, 150)
        # Rodapé centralizado
        texto_footer = f"Escrita Contabilidade | Gerado em {datetime.date.today().strftime('%d/%m/%Y')} | Pagina {self.page_no()}"
        self.cell(0, 10, texto_footer.encode('latin-1', 'ignore').decode('latin-1'), 0, 0, 'C')
        # Linha fina decorativa
        self.set_draw_color(200, 200, 200)
        self.line(10, 280, 200, 280)

def gerar_documento_proposta(dados_cliente, total):
    pdf = PDFProposta()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # --- BLOCO CLIENTE ---
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(10, 50, 190, 28, 'F') # Fundo para destaque
    
    pdf.set_xy(15, 53)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "CLIENTE APRESENTADO:", ln=True)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(26, 42, 68)
    nome_u = dados_cliente['nome'].upper().encode('latin-1', 'ignore').decode('latin-1')
    pdf.cell(0, 8, nome_u, ln=True)
    
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(50, 50, 50)
    seg_u = dados_cliente['segmento'].encode('latin-1', 'ignore').decode('latin-1')
    pdf.cell(0, 5, f"Segmento: {seg_u} | Data: {datetime.date.today().strftime('%d/%m/%Y')}", ln=True)
    
    # --- CONTEÚDO ---
    pdf.ln(15)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(26, 42, 68)
    pdf.cell(0, 10, "1. ESCOPO DOS SERVICOS", ln=True)
    
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(0, 0, 0)
    texto_intro = (
        "Nossa proposta abrange a assessoria contabil completa, focada em garantir a "
        "seguranca juridica e a otimizacao tributaria da sua empresa. Inclui os departamentos: "
        "Contabil, Fiscal e Trabalhista (Folha de Pagamento)."
    )
    pdf.multi_cell(0, 6, texto_intro.encode('latin-1', 'ignore').decode('latin-1'))
    
    # --- TABELA DE INVESTIMENTO ---
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(26, 42, 68) 
    pdf.set_text_color(255, 255, 255)
    
    pdf.cell(130, 12, "  Descricao do Investimento", 0, 0, 'L', True)
    pdf.cell(60, 12, "Valor Mensal  ", 0, 1, 'R', True)
    
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(230, 230, 230)
    
    pdf.cell(130, 15, "  Honorarios Mensais de Assessoria", 'B')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(60, 15, f"{formatar_moeda(total)}  ", 'B', 1, 'R')
    
    # --- CONDIÇÕES ---
    pdf.ln(15)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(26, 42, 68)
    pdf.cell(0, 10, "2. CONDICOES GERAIS", ln=True)
    
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(60, 60, 60)
    condicoes = (
        "- Validade: 10 dias corridos.\n"
        "- Reajuste: Anual pelo IGP-M/FGV.\n"
        "- Formalizacao: Assinatura digital via GOV.BR ou similar."
    )
    pdf.multi_cell(0, 6, condicoes.encode('latin-1', 'ignore').decode('latin-1'))
    
    # --- ASSINATURA ---
    pdf.ln(25)
    pdf.set_draw_color(26, 42, 68)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 5, "ACEITE DO CLIENTE", 0, 1, 'C')
    pdf.set_font("Arial", '', 8)
    pdf.cell(0, 5, "(Documento assinado digitalmente)", 0, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

# --- NAVEGAÇÃO LATERAL ---
if os.path.exists("Logo Escrita.png"):
    st.sidebar.image("Logo Escrita.png", width=200)
else:
    st.sidebar.title("Escrita Contabilidade")

menu = st.sidebar.selectbox("Navegação", ["Nova Proposta", "Configurações do Sistema"])

# --- MÓDULO: NOVA PROPOSTA ---
if menu == "Nova Proposta":
    st.title("📄 Elaboração de Proposta Comercial")
    
    segs = buscar_segmentos()
    lista_s = [s['nome'] for s in segs]
    
    if lista_s:
        c1, c2 = st.columns([2, 1])
        with c1:
            nome_cliente = st.text_input("Nome da Empresa / Prospecto:", placeholder="Ex: Labor Saúde LTDA")
        with c2:
            seg_sel = st.selectbox("Selecione o segmento:", lista_s)
        
        st.divider()
        
        perguntas = supabase.table("perguntas").select("*").eq("segmento", seg_sel).execute().data
        
        total = 0.0

        if perguntas:
            st.subheader("📋 Questionário de Diagnóstico")
            col_perg, col_espaco = st.columns([2, 1])
            
            with col_perg:
                for p in perguntas:
                    if "Múltipla Escolha" in p['tipo_campo']:
                        ops = [o.strip() for o in p['opcoes'].split(",")]
                        vls = [float(v.strip()) for v in p['pesos_opcoes'].split(",")]
                        esc = st.selectbox(p['pergunta'], ops, key=f"run_{p['id']}")
                        valor_item = vls[ops.index(esc)]
                        total += valor_item
                    else:
                        n_in = st.number_input(p['pergunta'], min_value=0, key=f"run_{p['id']}")
                        valor_item = (n_in * float(p['pesos_opcoes']))
                        total += valor_item
            
            st.divider()
            st.markdown(f'''
                <div class="metric-card">
                    <p style="margin:0; font-size: 1.2rem; opacity: 0.8;">Honorário Mensal Estimado</p>
                    <h2>{formatar_moeda(total)}</h2>
                    <p style="margin:0;">Foco em: {seg_sel}</p>
                </div>
            ''', unsafe_allow_html=True)
            
            st.write("") 
            
            if nome_cliente:
                pdf_bytes = gerar_documento_proposta(
                    {"nome": nome_cliente, "segmento": seg_sel}, 
                    total
                )
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    st.download_button(
                        label="📥 Baixar Proposta para Assinar",
                        data=pdf_bytes,
                        file_name=f"Proposta_Escrita_{nome_cliente.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                with c_btn2:
                    st.link_button("🖋️ Ir para Assinador GOV.BR", "https://www.gov.br/governodigital/pt-br/assinatura-eletronica", use_container_width=True)
            else:
                st.warning("⚠️ Digite o nome da empresa para habilitar a geração da proposta.")
        else:
            st.info("Nenhuma pergunta cadastrada para este segmento.")
    else:
        st.info("Cadastre os segmentos nas configurações primeiro.")

# --- MÓDULO: CONFIGURAÇÕES ---
elif menu == "Configurações do Sistema":
    st.title("⚙️ Gestão de Regras")
    t_seg, t_per = st.tabs(["📂 Segmentos", "❓ Perguntas"])

    with t_seg:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("Novo Segmento")
            n_seg = st.text_input("Nome do Segmento:")
            if st.button("Salvar Segmento"):
                supabase.table("segmentos").insert({"nome": n_seg}).execute()
                st.rerun()
        with c2:
            st.subheader("Lista de Segmentos")
            for s in buscar_segmentos():
                col_n, col_b = st.columns([3, 1])
                col_n.write(f"**{s['nome']}**")
                if col_b.button("Excluir", key=f"del_s_{s['id']}"):
                    supabase.from_("segmentos").delete().eq("id", s['id']).execute()
                    st.rerun()

    with t_per:
        st.subheader("Nova Pergunta de Cálculo")
        segs = buscar_segmentos()
        lista_nomes = [s['nome'] for s in segs]
        
        with st.form("cad_p"):
            c1, c2 = st.columns(2)
            f_seg = c1.selectbox("Segmento", lista_nomes)
            f_tipo = c2.selectbox("Tipo", ["Múltipla Escolha (Valor Fixo)", "Número (Multiplicador)"])
            f_perg = st.text_input("Pergunta (Ex: Qual o regime tributário?)")
            f_opt = st.text_input("Opções (Separe por vírgula: Sim, Não)")
            f_pesos = st.text_input("Pesos R$ (Separe por vírgula: 100, 50)")
            if st.form_submit_button("Salvar Regra de Preço"):
                supabase.table("perguntas").insert({
                    "segmento": f_seg, "pergunta": f_perg, "tipo_campo": f_tipo,
                    "opcoes": f_opt, "pesos_opcoes": f_pesos
                }).execute()
                st.rerun()

        st.divider()
        st.subheader("Perguntas Ativas no Banco")
        for p in buscar_perguntas():
            with st.expander(f"{p['segmento']} - {p['pergunta']}"):
                c_inf, c_del = st.columns([4, 1])
                c_inf.write(f"Configuração: {p['tipo_campo']} | Valores: {p['pesos_opcoes']}")
                if c_del.button("🗑️ Deletar", key=f"del_p_{p['id']}"):
                    supabase.from_("perguntas").delete().eq("id", p['id']).execute()
                    st.rerun()
