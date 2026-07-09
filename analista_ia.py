import pandas as pd
import streamlit as st
import google.generativeai as genai


def ler_excel(uploaded_file):
    if uploaded_file is None:
        return ""

    try:
        df = pd.read_excel(uploaded_file)
        return df.head(80).to_string(index=False)
    except Exception as e:
        return f"Erro ao ler Excel: {e}"


def gerar_parecer_ia(contexto):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
Você é um analista sênior de precificação contábil, controller e consultor empresarial.

Analise os dados abaixo e entregue um parecer objetivo para a Escrita Contabilidade.

Dados:
{contexto}

Responda obrigatoriamente nesta estrutura:

1. Diagnóstico executivo
2. Riscos operacionais
3. Análise da adequação do preço
4. Pontos que justificam aumento ou desconto
5. Preço mínimo recomendado
6. Preço ideal recomendado
7. Nota da oportunidade: A, B, C ou D
8. Recomendação comercial final

Se os dados forem insuficientes, diga claramente quais informações faltam.
Não invente números que não estejam nos dados.
"""

    resposta = model.generate_content(prompt)
    return resposta.text


def tela_analista_ia(supabase):
    st.title("🤖 Analista IA de Precificação")

    st.info(
        "Este módulo usa IA para interpretar os dados da proposta, DRE, balancete e documentos financeiros. "
        "Os cálculos principais continuam sendo feitos pelo CRM; a IA apenas gera o parecer consultivo."
    )

    st.subheader("Dados manuais da análise")

    col1, col2 = st.columns(2)

    with col1:
        nome_empresa = st.text_input("Empresa")
        segmento = st.text_input("Segmento")
        regime = st.selectbox("Regime", ["Simples", "Presumido", "Real", "Não sei"])
        valor_proposto = st.number_input("Valor proposto / honorário mensal", min_value=0.0, step=100.0)

    with col2:
        faturamento = st.number_input("Faturamento mensal estimado", min_value=0.0, step=1000.0)
        colaboradores_cliente = st.number_input("Colaboradores do cliente", min_value=0, step=1)
        notas_mes = st.number_input("Notas / documentos por mês", min_value=0, step=1)
        horas_estimadas = st.number_input("Horas estimadas da Escrita", min_value=0.0, step=1.0)

    st.divider()

    st.subheader("Anexos para análise")

    dre = st.file_uploader("DRE em Excel", type=["xlsx", "xlsm"], key="ia_dre")
    balancete = st.file_uploader("Balancete em Excel", type=["xlsx", "xlsm"], key="ia_balancete")
    folha = st.file_uploader("Folha / colaboradores em Excel", type=["xlsx", "xlsm"], key="ia_folha")
    outros = st.text_area("Observações adicionais")

    if st.button("Gerar análise com IA"):
        contexto = f"""
Empresa: {nome_empresa}
Segmento: {segmento}
Regime: {regime}
Valor proposto: {valor_proposto}
Faturamento mensal estimado: {faturamento}
Colaboradores do cliente: {colaboradores_cliente}
Notas/documentos por mês: {notas_mes}
Horas estimadas da Escrita: {horas_estimadas}
Observações: {outros}

DRE:
{ler_excel(dre)}

Balancete:
{ler_excel(balancete)}

Folha:
{ler_excel(folha)}
"""

        try:
            with st.spinner("Gerando parecer da IA..."):
                parecer = gerar_parecer_ia(contexto)

            st.success("Análise gerada com sucesso.")
            st.markdown(parecer)

        except Exception as e:
            st.error(f"Erro ao gerar análise com IA: {e}")
