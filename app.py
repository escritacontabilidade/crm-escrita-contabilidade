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

def get_config_val(chave):
    try:
        res = supabase.table("configuracao_operacional").select("valor").eq("chave", chave).execute()
        return float(res.data[0]['valor']) if res.data else 0.0
    except:
        return 0.0

def calcular_custo_hora_real():
    folha = get_config_val('total_folha')
    fixas = get_config_val('despesas_fixas')
    horas = get_config_val('horas_uteis_mes')
    equipe = get_config_val('num_colaboradores')
    custo_total = folha + fixas
    capacidade_horas = horas * equipe
    return custo_total / capacidade_horas if capacidade_horas > 0 else 0.0

def get_peso_esforco(regime, item):
    try:
        res = supabase.table("pesos_esforco").select("horas_esforco").eq("regime", regime).eq("item", item).execute()
        return float(res.data[0]['horas_esforco']) if res.data else 0.0
    except:
        return 0.0

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

# --- 5. LÓGICA DE ACESSO (CLIENTE VS CONTADOR) ---
query_params = st.query_params
is_cliente = query_params.get("modo") == "cliente"

if is_cliente:
    st.image("Logo Escrita.png", width=200)
    st.title("📝 Solicitação de Orçamento")
    st.write("Preencha os dados abaixo para receber nossa proposta comercial.")
    with st.form("form_externo"):
        f_empresa = st.text_input("Nome da Empresa")
        f_resp = st.text_input("Seu Nome")
        f_whatsapp = st.text_input("WhatsApp (com DDD)")
        f_regime = st.selectbox("Regime Atual", ["Simples", "Presumido", "Real", "Não sei"])
        c1, c2, c3 = st.columns(3)
        f_func = c1.number_input("Funcionários", min_value=0)
        f_notas = c2.number_input("Notas/Mês", min_value=0)
        f_lanc = c3.number_input("Lançamentos/Mês", min_value=0)
        if st.form_submit_button("Enviar Solicitação"):
            obj = {"nome_empresa": f_empresa, "responsavel": f_resp, "whatsapp": f_whatsapp, 
                   "regime": f_regime, "qtd_func": f_func, "qtd_notas": f_notas, "qtd_lanca": f_lanc}
            supabase.table("leads_externos").insert(obj).execute()
            st.success("✅ Recebemos seus dados! Entraremos em contato em breve.")
            st.stop()
else:
    if os.path.exists("Logo Escrita.png"):
        st.sidebar.image("Logo Escrita.png", width=200)
    menu = st.sidebar.selectbox("Navegação", ["Nova Proposta", "Dashboard de Custos", "Histórico de Vendas", "Configurações", "Link para Cliente"])

if menu == "Nova Proposta":
    st.title("📄 Elaboração de Proposta Precificada")
    
    # 1. Inputs de Identificação e Regime
    c1, c2 = st.columns([2, 1])
    nome_cliente = c1.text_input("Nome da Empresa:")
    regime_sel = c2.selectbox("Regime Tributário:", ["Simples", "Presumido", "Real"])
    
    # 2. Seleção de Segmento para carregar as Perguntas
    res_seg = supabase.table("segmentos").select("*").execute()
    lista_s = [s['nome'] for s in res_seg.data] if res_seg.data else []
    seg_sel = st.selectbox("Selecione o segmento do cliente:", lista_s)
    
    st.divider()

    # 3. Inputs de Volume (Esforço Contábil)
    col_a, col_b, col_c = st.columns(3)
    qtd_func = col_a.number_input("Nº Funcionários", min_value=0, step=1)
    qtd_notas = col_b.number_input("Qtd Notas Fiscais", min_value=0, step=1)
    qtd_lanca = col_c.number_input("Qtd Lançamentos", min_value=0, step=1)
    possui_filial = st.checkbox("Possui Filial?")
    
    # 4. Perguntas Dinâmicas do Segmento (Complexidade)
    total_pergunta_segmento = 0.0
    res_perg = supabase.table("perguntas").select("*").ilike("segmento", seg_sel).execute()
    
    if res_perg.data:
        st.subheader(f"📋 Diagnóstico Específico: {seg_sel}")
        for p in res_perg.data:
            if "Múltipla Escolha" in p['tipo_campo']:
                ops = [o.strip() for o in str(p['opcoes']).split(",")]
                vls = [float(v.strip()) for v in str(p['pesos_opcoes']).split(",")]
                esc = st.selectbox(p['pergunta'], ops, key=f"p_{p['id']}")
                total_pergunta_segmento += vls[ops.index(esc)]
            else:
                n_in = st.number_input(p['pergunta'], min_value=0, key=f"p_{p['id']}")
                total_pergunta_segmento += (n_in * float(p['pesos_opcoes']))

    st.divider()

    # 5. CÁLCULO DE HORAS (PESOS DO SUPABASE)
    h_base = get_peso_esforco(regime_sel, 'Base')
    p_func = get_peso_esforco(regime_sel, 'Funcionario')
    p_nota = get_peso_esforco(regime_sel, 'Nota Fiscal')
    p_lanc = get_peso_esforco(regime_sel, 'Lancamento')
    h_filial = get_peso_esforco('Filial', 'Adicional Base') if possui_filial else 0

    total_horas_est = h_base + h_filial + (qtd_func * p_func) + (qtd_notas * p_nota) + (qtd_lanca * p_lanc)
    
    c_hora_atual = calcular_custo_hora_real()
    perc_imposto = get_config_val('impostos_faturamento') / 100
    
    # O Custo Operacional é (Horas * Custo Hora) + Adicionais fixos das perguntas
    custo_operacional = (total_horas_est * c_hora_atual) + total_pergunta_segmento

    # 6. EXIBIÇÃO DOS 3 CARDS
    st.subheader("💰 Opções de Investimento")
    res1, res2, res3 = st.columns(3)

    def calcular_venda(margem):
        margem_decimal = margem / 100
        divisor = (1 - perc_imposto - margem_decimal)
        return custo_operacional / divisor if divisor > 0 else 0

    v_bronze = calcular_venda(20)
    v_prata = calcular_venda(35)
    v_ouro = calcular_venda(50)

    res1.markdown(f"""<div class="metric-card"><p>BRONZE (20%)</p><h2>{formatar_moeda(v_bronze)}</h2></div>""", unsafe_allow_html=True)
    res2.markdown(f"""<div class="metric-card"><p>PRATA (35%)</p><h2>{formatar_moeda(v_prata)}</h2></div>""", unsafe_allow_html=True)
    res3.markdown(f"""<div class="metric-card"><p>OURO (50%)</p><h2>{formatar_moeda(v_ouro)}</h2></div>""", unsafe_allow_html=True)

    # 7. SALVAMENTO
    if st.button("💾 Salvar Orçamento Final"):
        if nome_cliente:
            dados_venda = {
                "cliente": nome_cliente,
                "regime": regime_sel,
                "segmento": seg_sel,
                "valor_total": v_prata, # Salvando o Prata como padrão
                "horas_estimadas": total_horas_est
            }
            supabase.table("historico_vendas").insert(dados_venda).execute()
            st.success("Orçamento salvo com sucesso!")

# --- MÓDULOS DE APOIO (MANTIDOS E INTEGRADOS) ---
elif menu == "Dashboard de Custos":
    st.title("💰 Configuração de Custos Operacionais")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Custos de Estrutura")
        f_folha = st.number_input("Total Folha + Encargos (R$)", value=get_config_val('total_folha'))
        f_fixas = st.number_input("Despesas Fixas (Sistemas/Aluguel) (R$)", value=get_config_val('despesas_fixas'))
        f_imposto = st.number_input("Imposto Médio s/ Faturamento (%)", value=get_config_val('impostos_faturamento'))
    
    with col2:
        st.subheader("Capacidade Produtiva")
        f_horas = st.number_input("Horas Úteis por Colaborador/Mês", value=get_config_val('horas_uteis_mes'))
        f_equipe = st.number_input("Quantidade de Colaboradores", value=get_config_val('num_colaboradores'))

    if st.button("💾 Salvar e Atualizar Custo-Hora"):
        configs = [
            {"chave": "total_folha", "valor": f_folha},
            {"chave": "despesas_fixas", "valor": f_fixas},
            {"chave": "impostos_faturamento", "valor": f_imposto},
            {"chave": "horas_uteis_mes", "valor": f_horas},
            {"chave": "num_colaboradores", "valor": f_equipe}
        ]
        for c in configs:
            supabase.table("configuracao_operacional").upsert(c, on_conflict="chave").execute()
        st.success("Custo-Hora atualizado!")
        st.rerun()

    c_hora = calcular_custo_hora_real()
    st.divider()
    st.markdown(f"""<div class="metric-card"><p>Custo Hora Atual</p><h2>{formatar_moeda(c_hora)}</h2></div>""", unsafe_allow_html=True)

elif menu == "Link para Cliente":
    st.title("🔗 Coleta Externa de Dados")
    st.info("Envie o link abaixo para o prospecto preencher as informações iniciais.")
    st.code("https://seu-app.streamlit.app/?modo=cliente")
    
    st.divider()
    st.subheader("📥 Leads Recebidos")
    try:
        res = supabase.table("leads_externos").select("*").order("created_at", desc=True).execute()
        if res.data:
            st.dataframe(pd.DataFrame(res.data), use_container_width=True)
        else:
            st.write("Nenhum lead preenchido ainda.")
    except Exception as e:
        st.error(f"Erro ao carregar leads: {e}")
        
elif menu == "Histórico de Vendas":
    st.title("📊 Histórico de Orçamentos")
    res_h = supabase.table("historico_vendas").select("*").order("data_criacao", desc=True).execute()
    if res_h.data:
        st.dataframe(pd.DataFrame(res_h.data), use_container_width=True)

elif menu == "Configurações":
    st.title("⚙️ Painel de Controle e Cadastros")
    t1, t2, t3, t4 = st.tabs(["Segmentos e Perguntas", "Preços Avulsos", "Pesos de Esforço", "Custos Fixos"])
    
    with t1:
        st.subheader("1. Gestão de Segmentos")
        col_seg1, col_seg2 = st.columns([1, 2])
        with col_seg1:
            n_seg = st.text_input("Novo Segmento (Ex: Clínica):")
            if st.button("Salvar Segmento"):
                supabase.table("segmentos").insert({"nome": n_seg}).execute()
                st.rerun()
        with col_seg2:
            res_s = supabase.table("segmentos").select("*").execute()
            if res_s.data:
                df_s = pd.DataFrame(res_s.data)
                st.write("Segmentos Cadastrados:")
                st.dataframe(df_s[['nome']], use_container_width=True)

        st.divider()
        st.subheader("2. Gestão de Perguntas")
        with st.form("nova_pergunta"):
            f_seg = st.selectbox("Segmento Alvo", [s['nome'] for s in res_s.data] if res_s.data else [])
            f_tipo = st.selectbox("Tipo", ["Múltipla Escolha", "Número (Multiplicador)"])
            f_perg = st.text_input("Pergunta")
            f_opt = st.text_input("Opções (Ex: Sim, Não ou Pequeno, Médio)")
            f_pesos = st.text_input("Pesos (Ex: 100, 0 ou 50, 150)")
            if st.form_submit_button("Salvar Pergunta"):
                supabase.table("perguntas").insert({
                    "segmento": f_seg, "pergunta": f_perg, "tipo_campo": f_tipo,
                    "opcoes": f_opt, "pesos_opcoes": f_pesos
                }).execute()
                st.success("Pergunta salva!")

        # Visualização das Perguntas com Filtro
        st.write("---")
        st.write("🔍 Perguntas Existentes")
        filtro_p = st.selectbox("Filtrar por Segmento:", ["Todos"] + ([s['nome'] for s in res_s.data] if res_s.data else []))
        query_p = supabase.table("perguntas").select("*")
        if filtro_p != "Todos":
            query_p = query_p.eq("segmento", filtro_p)
        res_p = query_p.execute()
        if res_p.data:
            st.dataframe(pd.DataFrame(res_p.data)[['segmento', 'pergunta', 'opcoes', 'pesos_opcoes']], use_container_width=True)

    with t2:
        st.subheader("Serviços Avulsos (Tabela 2026)")
        with st.form("add_avulso"):
            st.text_input("Nome do Serviço", key="av_n")
            st.number_input("Valor (R$)", key="av_v")
            if st.form_submit_button("Adicionar Serviço"):
                supabase.table("servicos_avulsos").insert({"servico": st.session_state.av_n, "valor": st.session_state.av_v}).execute()
                st.rerun()
        
        res_av = supabase.table("servicos_avulsos").select("*").execute()
        if res_av.data:
            st.write("Lista de Serviços Cadastrados:")
            st.dataframe(pd.DataFrame(res_av.data)[['servico', 'valor']], use_container_width=True)

    with t3:
        st.subheader("Ajuste de Pesos de Esforço (Horas)")
        st.info("Aqui você altera quanto tempo cada item (Nota, Funcionário, etc) consome em cada regime.")
        res_pesos = supabase.table("pesos_esforco").select("*").execute()
        if res_pesos.data:
            df_pesos = pd.DataFrame(res_pesos.data)
            # Filtro por Regime
            reg_f = st.selectbox("Filtrar Regime:", ["Todos", "Simples", "Presumido", "Real", "Filial"])
            df_p_view = df_pesos if reg_f == "Todos" else df_pesos[df_pesos['regime'] == reg_f]
            st.dataframe(df_p_view[['regime', 'item', 'horas_esforco']], use_container_width=True)
            
            st.warning("Para editar esses valores, utilize o Table Editor do Supabase diretamente por enquanto (Segurança do Banco).")

    with t4:
        st.subheader("Custos Fixos (Visualização)")
        res_cf = supabase.table("configuracao_operacional").select("*").execute()
        if res_cf.data:
            st.dataframe(pd.DataFrame(res_cf.data)[['chave', 'valor']], use_container_width=True)
