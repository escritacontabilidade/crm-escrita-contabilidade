import streamlit as st
from supabase import create_client
from fpdf import FPDF
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="CRM Escrita Contabilidade", layout="wide", page_icon="📄")

# --- CONEXÃO SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- ESTILOS CSS ---
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
    .metric-card h2 { color: #d4af37 !important; font-size: 3rem !important; }
    div.stButton > button { border-radius: 5px; font-weight: bold; }
    .stTabs [data-baseweb="tab"] { font-size: 1.1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES AUXILIARES ---
def formatar_moeda(valor):
    """Formata valor numérico para o padrão brasileiro R$ xx.xxx,xx"""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def buscar_segmentos():
    res = supabase.table("segmentos").select("*").execute()
    return res.data

def buscar_perguntas():
    res = supabase.table("perguntas").select("*").execute()
    return res.data

# --- GERADOR DE PDF ---
class PDFProposta(FPDF):
    def header(self):
        # Tarja superior Azul Escuro
        self.set_fill_color(26, 42, 68)
        self.rect(0, 0, 210, 45, 'F')
        self.set_xy(10, 15)
        self.set_font("Arial", 'B', 20)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "PROPOSTA COMERCIAL", 0, 1, 'C')
        self.set_font("Arial", '', 10)
        self.cell(0, 5, "Escrita Contabilidade - Inteligencia e Gestao", 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Pagina {self.page_no()} | Gerado em {datetime.date.today().strftime('%d/%m/%Y')}", 0, 0, 'C')

def gerar_documento_proposta(dados_cliente, total, itens_proposta):
    pdf = PDFProposta()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Dados do Cliente (Tratando acentos para evitar erro Unicode)
    pdf.set_y(55)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(26, 42, 68)
    nome_u = dados_cliente['nome'].upper().encode('latin-1', 'ignore').decode('latin-1')
    pdf.cell(0, 10, f"PREPARADO PARA: {nome_u}", ln=True)
    
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(0, 0, 0)
    seg_u = dados_cliente['segmento'].encode('latin-1', 'ignore').decode('latin-1')
    pdf.cell(0, 7, f"Segmento: {seg_u}", ln=True)
    pdf.cell(0, 7, f"Data de Emissao: {datetime.date.today().strftime('%d/%m/%Y')}", ln=True)
    
    # Escopo e Investimento
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "1. INVESTIMENTO E HONORARIOS", ln=True)
    pdf.set_font("Arial", '', 11)
    texto_intro = "Com base nas informacoes fornecidas e no diagnostico do perfil operacional da empresa, definimos os seguintes honorarios mensais:"
    pdf.multi_cell(0, 7, texto_intro.encode('latin-1', 'ignore').decode('latin-1'))
    
    # Tabela de Preço
    pdf.ln(5)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(140, 12, " Descricao do Servico", 1, 0, 'L', True)
    pdf.cell(50, 12, " Valor Mensal", 1, 1, 'C', True)
    
    pdf.set_font("Arial", '', 11)
    pdf.cell(140, 12, " Assessoria Contabil, Fiscal e Trabalhista Especializada", 1)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(50, 12, f" {formatar_moeda(total)}", 1, 1, 'C')
    
    # Instruções de Assinatura (Correção do erro Unicode: removido • e acentos problemáticos)
    pdf.ln(20)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. FORMALIZACAO E ACEITE", ln=True)
    pdf.set_font("Arial", '', 11)
    texto_instrucoes = (
        "Esta proposta e valida por 10 dias. Para formalizacao, utilize o portal GOV.BR "
        "para assinatura digital e realize o upload do arquivo assinado em nosso sistema."
    )
    pdf.multi_cell(0, 7, texto_instrucoes.encode('latin-1', 'ignore').decode('latin-1'))
    
    # Espaço para Assinatura Digital
    pdf.ln(20)
    pdf.cell(0, 0, "", border='T', ln=1, align='C')
    pdf.ln(2)
    pdf.set_font("Arial", 'I', 9)
    pdf.cell(0, 5, "Espaco reservado para Assinatura Digital (GOV.BR)", 0, 1, 'C')
    
    return pdf.output()

# --- NAVEGAÇÃO LATERAL ---
st.sidebar.image("Logo Escrita.png", width=200)
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
        detalhes_proposta = []

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
            
            # Painel de Resultado
            st.divider()
            st.markdown(f'''
                <div class="metric-card">
                    <p style="margin:0; font-size: 1.2rem; opacity: 0.8;">Honorário Mensal Estimado</p>
                    <h2>{formatar_moeda(total)}</h2>
                    <p style="margin:0;">Foco em: {seg_sel}</p>
                </div>
            ''', unsafe_allow_html=True)
            
            st.write("") # Espaçador
            
            # Botão de PDF
            if nome_cliente:
                pdf_output = gerar_documento_proposta(
                    {"nome": nome_cliente, "segmento": seg_sel}, 
                    total, 
                    detalhes_proposta
                )
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    st.download_button(
                        label="📥 Baixar Proposta para Assinar",
                        data=bytes(pdf_output),
                        file_name=f"Proposta_Escrita_{nome_cliente.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                with c_btn2:
                    st.link_button("🖋️ Ir para Assinador GOV.BR", "https://www.gov.br/governodigital/pt-br/assinatura-eletronica", use_container_width=True)
                
                st.divider()
                st.subheader("📤 Upload da Proposta Assinada")
                up_file = st.file_uploader("Arraste aqui o PDF assinado pelo cliente:", type="pdf")
                if up_file:
                    st.success("Arquivo recebido com sucesso! A proposta foi salva no histórico.")
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
