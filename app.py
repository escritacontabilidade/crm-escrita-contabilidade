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

# --- ESTILOS CSS CORPORATIVOS (Sua Versão de Produção) ---
st.markdown("""
    <style>
    .metric-card { 
        background-color: #1a2a44; 
        padding: 30px; 
        border-radius: 15px; 
        color: white; 
        text-align: center;
        border: 2px solid #d4af37;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .metric-card h2 { color: #d4af37 !important; font-size: 3rem !important; margin: 10px 0; }
    .metric-card p { font-size: 1.1rem; opacity: 0.9; }
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

# --- GERADOR DE PDF PREMIUM (Inspirado no 4C) ---
class PDFProposta(FPDF):
    def header(self):
        # Tarja superior Azul Escuro Escrita
        self.set_fill_color(26, 42, 68)
        self.rect(0, 0, 210, 45, 'F')
        # Linha Dourada de detalhe
        self.set_fill_color(212, 175, 55)
        self.rect(0, 45, 210, 2, 'F')
        
        self.set_xy(10, 15)
        self.set_font("Arial", 'B', 20)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "PROPOSTA DE SERVIÇOS CONTÁBEIS", 0, 1, 'C')
        self.set_font("Arial", '', 10)
        self.cell(0, 5, "Escrita Contabilidade - Inteligência e Gestão", 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Escrita Contabilidade | Gerado em {datetime.date.today().strftime('%d/%m/%Y')} | Página {self.page_no()}", 0, 0, 'C')

def gerar_documento_proposta(dados_cliente, total):
    pdf = PDFProposta()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Dados do Cliente
    pdf.set_y(60)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(26, 42, 68)
    pdf.cell(0, 10, f"À EMPRESA: {dados_cliente['nome'].upper()}", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 7, f"Segmento Atendido: {dados_cliente['segmento']}", ln=True)
    pdf.cell(0, 7, f"Identificador da Proposta: #{datetime.datetime.now().strftime('%Y%m%d%H%M')}", ln=True)
    
    # Introdução Técnica
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(0, 10, "1. APRESENTAÇÃO", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 7, "A Escrita Contabilidade propõe uma assessoria contábil consultiva, focada na conformidade tributária e no suporte à tomada de decisão para o seu negócio. Abaixo, detalhamos o investimento mensal para manutenção da sua operação.")
    
    # Tabela de Honorários
    pdf.ln(8)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(140, 12, " Descrição do Escopo Mensal", 1, 0, 'L', True)
    pdf.cell(50, 12, " Valor Mensal", 1, 1, 'C', True)
    
    pdf.set_font("Arial", '', 11)
    pdf.cell(140, 12, " Assessoria Técnica (Contábil, Fiscal e DP)", 1)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(50, 12, f" {formatar_moeda(total)}", 1, 1, 'C')
    
    # Termos e Validade
    pdf.ln(15)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. VALIDADE E ACEITE", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 7, "• Validade desta Proposta: 10 (dez) dias.\n• Reajuste: Anual conforme variação do IGP-M.\n• Formalização: Esta proposta deve ser assinada digitalmente (GOV.BR ou similar) e devolvida através do nosso sistema.")
    
    # Área de Assinatura
    pdf.ln(25)
    pdf.cell(0, 0, "", border='T', ln=1, align='C')
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 5, "ACEITE DO CLIENTE", 0, 1, 'C')
    pdf.set_font("Arial", 'I', 9)
    pdf.cell(0, 5, "Assinatura via portal GOV.BR", 0, 1, 'C')
    
    return pdf.output()

# --- NAVEGAÇÃO LATERAL ---
st.sidebar.image("Logo Escrita.png", width=200)
menu = st.sidebar.selectbox("Navegação", ["Nova Proposta", "Configurações do Sistema"])

# --- MÓDULO: NOVA PROPOSTA (Simulador Completo) ---
if menu == "Nova Proposta":
    st.title("📄 Elaboração de Proposta Comercial")
    
    segs = buscar_segmentos()
    lista_s = [s['nome'] for s in segs]
    
    if lista_s:
        # Layout de entrada
        c_nome, c_seg = st.columns([2, 1])
        with c_nome:
            nome_cliente = st.text_input("Nome da Empresa / Prospecto:", placeholder="Ex: Labor Saúde LTDA")
        with c_seg:
            seg_sel = st.selectbox("Selecione o segmento:", lista_s)
        
        st.divider()
        
        # Busca perguntas do banco
        perguntas = supabase.table("perguntas").select("*").eq("segmento", seg_sel).execute().data
        
        total = 0.0
        if perguntas:
            st.subheader("📋 Diagnóstico de Atividades")
            
            # Divide o questionário em duas colunas para não ficar muito longo
            col_perg, col_vazio = st.columns([2, 1])
            with col_perg:
                for p in perguntas:
                    if "Múltipla Escolha" in p['tipo_campo']:
                        # Tratamento das opções e pesos
                        ops = [o.strip() for o in p['opcoes'].split(",")]
                        vls = [float(v.strip()) for v in p['pesos_opcoes'].split(",")]
                        esc = st.selectbox(p['pergunta'], ops, key=f"run_{p['id']}")
                        total += vls[ops.index(esc)]
                    else:
                        n_in = st.number_input(p['pergunta'], min_value=0, key=f"run_{p['id']}")
                        total += (n_in * float(p['pesos_opcoes']))
            
            # EXIBIÇÃO DO RESULTADO (Sua métrica de produção)
            st.divider()
            st.markdown(f'''
                <div class="metric-card">
                    <p style="margin:0;">Valor do Honorário Mensal</p>
                    <h2>{formatar_moeda(total)}</h2>
                    <p style="margin:0; opacity: 0.7;">Análise baseada no segmento: {seg_sel}</p>
                </div>
            ''', unsafe_allow_html=True)
            
            # GERAÇÃO DA PROPOSTA
            st.write("") # Espaçador
            if nome_cliente:
                c_pdf, c_gov = st.columns(2)
                
                with c_pdf:
                    pdf_bytes = gerar_documento_proposta({"nome": nome_cliente, "segmento": seg_sel}, total)
                    st.download_button(
                        label="📥 Baixar Proposta para Assinar",
                        data=bytes(pdf_bytes),
                        file_name=f"Proposta_Escrita_{nome_cliente.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                with c_gov:
                    st.link_button("🖋️ Ir para Assinador GOV.BR", "https://www.gov.br/governodigital/pt-br/assinatura-eletronica", use_container_width=True)
                
                st.divider()
                st.subheader("📤 Retorno do Documento")
                up_file = st.file_uploader("Upload da Proposta Assinada:", type="pdf")
                if up_file:
                    st.success("Arquivo recebido! Documento salvo para conferência.")
            else:
                st.info("💡 Informe o nome da empresa acima para gerar o PDF da proposta.")
        else:
            st.info("Nenhuma regra de cálculo cadastrada para este segmento.")
    else:
        st.info("Acesse 'Configurações' para cadastrar seu primeiro segmento.")

# --- MÓDULO: CONFIGURAÇÕES (Gestão Total) ---
elif menu == "Configurações do Sistema":
    st.title("⚙️ Gestão de Regras")
    t_seg, t_per = st.tabs(["📂 Segmentos", "❓ Perguntas"])

    with t_seg:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("Novo Segmento")
            n_seg = st.text_input("Nome do Segmento (Ex: Clínica Médica):")
            if st.button("Salvar Segmento"):
                supabase.table("segmentos").insert({"nome": n_seg}).execute()
                st.rerun()
        with c2:
            st.subheader("Segmentos Ativos")
            for s in buscar_segmentos():
                col_n, col_b = st.columns([3, 1])
                col_n.write(f"**{s['nome']}**")
                if col_b.button("Excluir", key=f"del_s_{s['id']}"):
                    supabase.from_("segmentos").delete().eq("id", s['id']).execute()
                    st.rerun()

    with t_per:
        st.subheader("Cadastrar Regra de Preço")
        segs = buscar_segmentos()
        lista_nomes = [s['nome'] for s in segs]
        
        with st.form("cad_p"):
            c1, c2 = st.columns(2)
            f_seg = c1.selectbox("Segmento", lista_nomes)
            f_tipo = c2.selectbox("Tipo de Cálculo", ["Múltipla Escolha (Valor Fixo)", "Número (Multiplicador)"])
            f_perg = st.text_input("Texto da Pergunta:")
            f_opt = st.text_input("Opções (Separadas por vírgula. Ex: Sim, Não)")
            f_pesos = st.text_input("Valores R$ (Na mesma ordem das opções. Ex: 200, 0)")
            
            if st.form_submit_button("✅ Salvar Regra"):
                supabase.table("perguntas").insert({
                    "segmento": f_seg, "pergunta": f_perg, "tipo_campo": f_tipo,
                    "opcoes": f_opt, "pesos_opcoes": f_pesos
                }).execute()
                st.rerun()

        st.divider()
        st.subheader("Visualizar Regras Cadastradas")
        for p in buscar_perguntas():
            with st.expander(f"📍 {p['segmento']} - {p['pergunta']}"):
                c_inf, c_del = st.columns([4, 1])
                c_inf.write(f"**Tipo:** {p['tipo_campo']} | **Valores:** {p['pesos_opcoes']}")
                if c_del.button("🗑️ Deletar", key=f"del_p_{p['id']}"):
                    supabase.from_("perguntas").delete().eq("id", p['id']).execute()
                    st.rerun()
