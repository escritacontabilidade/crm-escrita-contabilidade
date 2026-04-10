import streamlit as st
import pandas as pd
import os

from database import (
    get_supabase,
    fetch_table,
    insert_data,
    upsert_data,
    get_config_val,
    get_origem_perguntas,
    get_perguntas_por_origem,
)
from pricing import calcular_custo_hora_real, calcular_precificacao_completa
from validators import (
    validar_campos_basicos_cliente,
    validar_formulario_lead,
    validar_pergunta_segmento,
)
from pdf_builder import gerar_pdf
from utils import formatar_moeda

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="CRM & Precificação Escrita", layout="wide", page_icon="📄")

try:
    supabase = get_supabase()
except Exception as e:
    st.error(f"Erro de conexão com o Supabase: {e}")
    st.stop()

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


# --- 5. LÓGICA DE ACESSO (CLIENTE VS CONTADOR) ---
query_params = st.query_params
is_cliente = query_params.get("modo") == "cliente"

if is_cliente:
    st.image("Logo Escrita.png", width=200)
    st.title("📝 Solicitação de Orçamento")
    st.write("Preencha os dados abaixo para receber nossa proposta comercial.")

    # 1. Busca os segmentos
    res_seg = supabase.table("segmentos").select("nome").execute()
    lista_segmentos = [s["nome"] for s in res_seg.data] if res_seg.data else []

    # 2. Cliente escolhe um ou mais segmentos
    res_regras = supabase.table("regras_segmento").select("segmentos").execute()
    lista_segmentos = [r["segmentos"] for r in res_regras.data] if res_regras.data else []
    
    f_segmento = st.selectbox(
        "Selecione o segmento da empresa",
        lista_segmentos
    )
    # 3. Busca perguntas pela origem correta
    res_perg_data = []

    if f_segmento:
        try:
            origem_perguntas = get_origem_perguntas(f_segmento)

            res_perg_data = get_perguntas_por_origem(origem_perguntas)
        except Exception as e:
            st.error(f"Erro ao carregar perguntas do segmento: {e}")

    with st.form("form_externo"):
        f_empresa = st.text_input("Nome da Empresa")
        f_resp = st.text_input("Seu Nome")
        f_whatsapp = st.text_input("WhatsApp (com DDD)")
        f_regime = st.selectbox("Regime Atual", ["Simples", "Presumido", "Real", "Não sei"])
    
        st.divider()
        st.subheader("Informações Gerais")
    
        faturamento_medio = st.number_input(
            "Faturamento médio mensal (R$)",
            min_value=0.0,
            step=1000.0,
            format="%.2f",
            value=0.0,
            key="cli_faturamento"
        )
        
        descricao_atividades = st.text_area(
            "Breve descrição sobre as atividades exercidas pela empresa",
            value="",
            key="cli_descricao"
        )
    
        respostas_extras = {}
        if res_perg_data:
            st.divider()
            st.subheader("Informações Adicionais")
    
            for p in res_perg_data:
                st.markdown(f"**{p['pergunta']}**")

                if "Múltipla Escolha" in p["tipo_campo"]:
                    ops = [o.strip() for o in str(p["opcoes"]).split(",") if o.strip()]
                    respostas_extras[p["pergunta"]] = st.radio(
                        "Selecione uma opção:",
                        ops,
                        key=f"ext_{p['id']}"
                    )
                elif p["tipo_campo"] == "Texto Livre":
                    respostas_extras[p["pergunta"]] = st.text_area(
                        "Digite sua resposta:",
                        key=f"ext_{p['id']}"
                    )
                else:
                    respostas_extras[p["pergunta"]] = st.number_input(
                        "Informe a quantidade:",
                        min_value=0,
                        step=1,
                        key=f"ext_{p['id']}"
                    )

                st.write("")

        if st.form_submit_button("Enviar Solicitação"):
            erros = validar_formulario_lead(f_empresa, f_resp, f_whatsapp, f_segmento)

            if erros:
                for erro in erros:
                    st.warning(erro)
            else:
                try:
                    obj = {
                        "nome_empresa": f_empresa,
                        "responsavel": f_resp,
                        "whatsapp": f_whatsapp,
                        "regime": f_regime,
                        "segmento": f_segmento,
                        "faturamento_medio": faturamento_medio,
                        "descricao_atividades": descricao_atividades,
                        "respostas_segmento": respostas_extras
                    }
                    insert_data("leads_externos", obj)
                    st.success("✅ Recebemos seus dados! Entraremos em contato em breve.")
                    st.stop()
                except Exception as e:
                    st.error(f"Erro ao salvar lead: {e}")
else:
    if os.path.exists("Logo Escrita.png"):
        st.sidebar.image("Logo Escrita.png", width=200)
    menu = st.sidebar.selectbox(
        "Navegação",
        ["Leads Recebidos", "Nova Proposta", "Proposta Comercial", "Dashboard de Custos", "Histórico de Vendas", "Configurações", "Link para Cliente"]
    )

    if menu == "Leads Recebidos":
        st.title("📥 Leads Recebidos")

        try:
            res_leads = supabase.table("leads_externos").select("*").order("created_at", desc=True).execute()

            if res_leads.data:
                df_leads = pd.DataFrame(res_leads.data)

                colunas_exibir = [
                    "id",
                    "nome_empresa",
                    "responsavel",
                    "segmento",
                    "regime",
                    "status",
                    "created_at"
                ]
                colunas_exibir = [c for c in colunas_exibir if c in df_leads.columns]

                st.dataframe(df_leads[colunas_exibir], use_container_width=True)

                lista_opcoes = [
                    f"{row['id']} | {row['nome_empresa']} | {row['segmento']}"
                    for _, row in df_leads.iterrows()
                ]

                lead_escolhido = st.selectbox(
                    "Selecione um lead para analisar",
                    lista_opcoes
                )

                if st.button("Carregar para Precificação"):
                    lead_id = int(lead_escolhido.split("|")[0].strip())
                    lead_data = df_leads[df_leads["id"] == lead_id].iloc[0].to_dict()

                    st.session_state["lead_em_analise"] = lead_data

                    try:
                        supabase.table("leads_externos").update({
                            "status": "Em análise"
                        }).eq("id", lead_id).execute()
                    except Exception as e:
                        st.warning(f"Não foi possível atualizar o status do lead: {e}")

                    st.success("Lead carregado. Agora vá para 'Nova Proposta'.")
            else:
                st.info("Nenhum lead recebido ainda.")

        except Exception as e:
            st.error(f"Erro ao carregar leads: {e}")
            
    if menu == "Nova Proposta":
            st.title("📄 Elaboração de Proposta Precificada")
            lead_em_analise = st.session_state.get("lead_em_analise", {})
        
            # 1. Inputs de Identificação e Regime
            c1, c2 = st.columns([2, 1])

            nome_cliente = c1.text_input(
                "Nome da Empresa:",
                value=lead_em_analise.get("nome_empresa", "")
            )
            
            opcoes_regime = ["Simples", "Presumido", "Real"]
            regime_padrao = lead_em_analise.get("regime", "Simples")
            if regime_padrao not in opcoes_regime:
                regime_padrao = "Simples"
            
            regime_sel = c2.selectbox(
                "Regime Tributário:",
                opcoes_regime,
                index=opcoes_regime.index(regime_padrao)
            )

            st.divider()
            st.subheader("Informações Gerais")
            
            faturamento_medio = st.number_input(
                "Faturamento médio mensal (R$)",
                min_value=0.0,
                step=1000.0,
                format="%.2f",
                value=float(lead_em_analise.get("faturamento_medio") or 0),
                key="np_faturamento"
            )
            
            descricao_atividades = st.text_area(
                "Breve descrição sobre as atividades exercidas pela empresa",
                value=lead_em_analise.get("descricao_atividades", "") or "",
                key="cli_descricao"
            )
    
            # 2. Seleção de Segmento para carregar as Perguntas
            res_seg = supabase.table("segmentos").select("*").execute()
            lista_s = [s["nome"] for s in res_seg.data] if res_seg.data else []
            
            res_regras = supabase.table("regras_segmento").select("segmentos").execute()
            lista_segmentos = [r["segmentos"] for r in res_regras.data] if res_regras.data else []
    
            segmento_padrao = lead_em_analise.get("segmento", "")
            if segmento_padrao not in lista_segmentos and lista_segmentos:
                segmento_padrao = lista_segmentos[0]
    
            seg_sel = st.selectbox(
                "Selecione o segmento do cliente:",
                lista_segmentos,
                index=lista_segmentos.index(segmento_padrao) if segmento_padrao in lista_segmentos else 0
            )
    
            st.divider()
            # Valores padrão enquanto os volumes passam a vir apenas das perguntas
            qtd_func = 0
            qtd_notas = 0
            qtd_lanca = 0
            possui_filial = False
        
            # 4. Perguntas Dinâmicas do Segmento (Complexidade)
            total_pergunta_segmento = 0.0
            res_perg_data = []
            
            if seg_sel:
                try:
                    origem_perguntas = get_origem_perguntas(seg_sel)
                    res_perg_data = get_perguntas_por_origem(origem_perguntas)
                    st.caption(f"Origem das perguntas utilizada: {origem_perguntas}")
                except Exception as e:
                    st.error(f"Erro ao carregar perguntas do segmento: {e}")
                        
            if res_perg_data:
                st.subheader(f"📋 Diagnóstico Específico: {seg_sel}")
            
                respostas_lead = lead_em_analise.get("respostas_segmento", {}) or {}
            
                if not isinstance(respostas_lead, dict):
                    respostas_lead = {}
            
               

                for p in res_perg_data:
                    st.markdown(f"**{p['pergunta']}**")

                    pergunta_texto = str(p.get("pergunta", "")).strip()
                    resposta_inicial = respostas_lead.get(pergunta_texto, None)
            
                    if "Múltipla Escolha" in p["tipo_campo"]:
                        ops = [o.strip() for o in str(p.get("opcoes", "")).split(",") if o.strip()]
                        vls = [float(v.strip().replace(",", ".")) for v in str(p.get("pesos_opcoes", "")).split(",") if v.strip()]

                        if len(ops) != len(vls):
                            st.error(f"Erro na pergunta: {pergunta_texto}")
                            continue

                        indice_padrao = 0
                        if resposta_inicial in ops:
                            indice_padrao = ops.index(resposta_inicial)

                        esc = st.radio(
                            "Selecione uma opção:",
                            ops,
                            index=indice_padrao,
                            key=f"p_{p['id']}"
                        )

                        total_pergunta_segmento += vls[ops.index(esc)]

                    elif p["tipo_campo"] == "Texto Livre":
                        st.text_area(
                            "Digite sua resposta:",
                            value=str(resposta_inicial or ""),
                            key=f"p_{p['id']}"
                        )

                    else:
                        valor_inicial = 0
                        try:
                            if resposta_inicial not in [None, ""]:
                                valor_inicial = int(float(resposta_inicial))
                        except:
                            valor_inicial = 0

                        peso_num = float(str(p.get("pesos_opcoes", "0")).replace(",", "."))

                        n_in = st.number_input(
                            "Informe a quantidade:",
                            min_value=0,
                            step=1,
                            value=valor_inicial,
                            key=f"p_{p['id']}"
                        )

                        total_pergunta_segmento += (n_in * peso_num)
            
                    st.write("")
    
            st.divider()
    
            # 5. Validação e cálculo
            erros = validar_campos_basicos_cliente(nome_cliente, regime_sel, seg_sel)
            for erro in erros:
                st.warning(erro)
    
            valores = None
            memoria = None
    
            if not erros:
                try:
                    valores, memoria = calcular_precificacao_completa(
                        regime_sel=regime_sel,
                        qtd_func=qtd_func,
                        qtd_notas=qtd_notas,
                        qtd_lanca=qtd_lanca,
                        possui_filial=possui_filial,
                        total_pergunta_segmento=total_pergunta_segmento,
                    )
                except Exception as e:
                    st.error(f"Erro no cálculo da precificação: {e}")
    
            # 6. Exibição dos cards
            if valores:
                st.subheader("💰 Opções de Investimento")
                res1, res2, res3 = st.columns(3)
    
                v_bronze = valores["bronze"]
                v_prata = valores["prata"]
                v_ouro = valores["ouro"]
    
                res1.markdown(
                    f"""<div class="metric-card"><p>BRONZE (20%)</p><h2>{formatar_moeda(v_bronze)}</h2></div>""",
                    unsafe_allow_html=True
                )
                res2.markdown(
                    f"""<div class="metric-card"><p>PRATA (35%)</p><h2>{formatar_moeda(v_prata)}</h2></div>""",
                    unsafe_allow_html=True
                )
                res3.markdown(
                    f"""<div class="metric-card"><p>OURO (50%)</p><h2>{formatar_moeda(v_ouro)}</h2></div>""",
                    unsafe_allow_html=True
                )
    
                with st.expander("Ver memória do cálculo"):
                    st.json(memoria)
    
                # 7. Salvamento
                if st.button("💾 Salvar Orçamento Final"):
                    try:
                        dados_venda = {
                            "cliente": nome_cliente,
                            "regime": regime_sel,
                            "segmento": seg_sel,
                            "faturamento_medio": faturamento_medio,
                            "descricao_atividades": descricao_atividades,
                            "valor_total": v_prata,
                            "horas_estimadas": memoria["horas_estimadas"],
                        }
                        insert_data("historico_vendas", dados_venda)
                        st.success("Orçamento salvo com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao salvar orçamento: {e}")    
    
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
        st.code("https://crm-escrita-contabilidade.streamlit.app/?modo=cliente")
        
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
                    erros = validar_pergunta_segmento(f_tipo, f_perg, f_opt, f_pesos)

                    if erros:
                        for erro in erros:
                            st.warning(erro)
                    else:
                        try:
                            supabase.table("perguntas").insert({
                                "segmento": f_seg,
                                "pergunta": f_perg,
                                "tipo_campo": f_tipo,
                                "opcoes": f_opt,
                                "pesos_opcoes": f_pesos
                            }).execute()
                            st.success("Pergunta salva!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar pergunta: {e}")
    
            # Visualização das Perguntas com Filtro
            st.write("---")
            st.write("🔍 Perguntas Existentes")
            filtro_p = st.selectbox("Filtrar por Segmento:", ["Todos"] + ([s['nome'] for s in res_s.data] if res_s.data else []))
            query_p = supabase.table("perguntas").select("*")
            if filtro_p != "Todos":
                query_p = query_p.eq("segmento", filtro_p)
            res_p = query_p.execute()
            if res_p.data:
                df_perg = pd.DataFrame(res_p.data)
            
                colunas_desejadas = ['origem', 'pergunta', 'tipo_campo', 'opcoes', 'pesos_opcoes']
                colunas_existentes = [c for c in colunas_desejadas if c in df_perg.columns]
            
                st.dataframe(df_perg[colunas_existentes], use_container_width=True)
            else:
                st.info("Nenhuma pergunta cadastrada.")
                   
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
