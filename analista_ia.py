import pandas as pd
import streamlit as st
import google.generativeai as genai


def formatar_brl(valor):
    try:
        return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def ler_excel(uploaded_file):
    if uploaded_file is None:
        return "Arquivo não enviado."

    try:
        df = pd.read_excel(uploaded_file)
        return df.head(100).to_string(index=False)
    except Exception as e:
        return f"Erro ao ler Excel: {e}"


def gerar_parecer_ia(contexto):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
Você é um analista sênior de precificação contábil, controller e consultor empresarial.

Analise os dados abaixo para a Escrita Contabilidade.

{contexto}

Responda nesta estrutura:

1. Diagnóstico executivo
2. Riscos operacionais
3. Análise da adequação do preço
4. Pontos que justificam aumento ou desconto
5. Preço mínimo recomendado
6. Preço ideal recomendado
7. Nota da oportunidade: A, B, C ou D
8. Recomendação comercial final

Não invente números. Se faltar dado, diga claramente.
"""

    resposta = model.generate_content(prompt)
    return resposta.text


def classificar_proposta(row):
    valor_final = float(row.get("valor_final") or 0)
    valor_calculado = float(row.get("valor_calculado") or 0)

    if valor_final <= 0:
        return "🔴 Sem valor"

    if valor_calculado <= 0:
        return "⚪ Sem base"

    diferenca = ((valor_final - valor_calculado) / valor_calculado) * 100

    if diferenca < -10:
        return "🔴 Abaixo do calculado"
    elif diferenca <= 10:
        return "🟡 Dentro da faixa"
    else:
        return "🟢 Acima do calculado"


def carregar_orcamentos(supabase):
    res = supabase.table("orcamentos") \
        .select("*") \
        .eq("ativo", True) \
        .order("created_at", desc=True) \
        .execute()

    return pd.DataFrame(res.data or [])


def tela_visao_geral(supabase):
    st.subheader("1. Visão Geral das Propostas")

    df = carregar_orcamentos(supabase)

    if df.empty:
        st.info("Nenhuma proposta encontrada.")
        return

    if "valor_calculado" not in df.columns:
        df["valor_calculado"] = 0

    if "valor_final" not in df.columns:
        df["valor_final"] = 0

    df["diferenca_valor"] = df["valor_final"].fillna(0) - df["valor_calculado"].fillna(0)

    df["diferenca_percentual"] = df.apply(
        lambda row: ((float(row.get("valor_final") or 0) - float(row.get("valor_calculado") or 0)) / float(row.get("valor_calculado") or 1)) * 100
        if float(row.get("valor_calculado") or 0) > 0 else 0,
        axis=1
    )

    df["classificacao_inicial"] = df.apply(classificar_proposta, axis=1)

    colunas = [
        "id",
        "cliente",
        "segmento",
        "regime",
        "plano",
        "valor_calculado",
        "valor_final",
        "diferenca_valor",
        "diferenca_percentual",
        "classificacao_inicial",
        "status",
        "created_at"
    ]

    colunas = [c for c in colunas if c in df.columns]

    st.dataframe(df[colunas], use_container_width=True)

    st.divider()

    total_propostas = len(df)
    total_valor = df["valor_final"].fillna(0).sum()
    ticket_medio = total_valor / total_propostas if total_propostas > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total de propostas", total_propostas)
    c2.metric("Valor mensal total", formatar_brl(total_valor))
    c3.metric("Ticket médio", formatar_brl(ticket_medio))


def tela_analise_individual(supabase):
    st.subheader("2. Análise Individual com IA")

    df = carregar_orcamentos(supabase)

    if df.empty:
        st.info("Nenhuma proposta encontrada.")
        return

    opcoes = [
        f"{row['id']} | {row.get('cliente', '')} | {row.get('segmento', '')} | {formatar_brl(row.get('valor_final') or 0)}"
        for _, row in df.iterrows()
    ]

    escolha = st.selectbox("Passo 1 — Escolha uma proposta", opcoes)

    orcamento_id = int(escolha.split("|")[0].strip())
    proposta = df[df["id"] == orcamento_id].iloc[0].to_dict()

    st.divider()
    st.markdown("### Dados da proposta")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cliente", proposta.get("cliente", ""))
    c2.metric("Segmento", proposta.get("segmento", ""))
    c3.metric("Regime", proposta.get("regime", ""))
    c4.metric("Valor final", formatar_brl(proposta.get("valor_final") or 0))

    st.divider()
    st.markdown("### Passo 2 — Anexe documentos financeiros")

    dre = st.file_uploader("DRE em Excel", type=["xlsx", "xlsm"], key="ia_dre")
    balancete = st.file_uploader("Balancete em Excel", type=["xlsx", "xlsm"], key="ia_balancete")
    folha = st.file_uploader("Folha / colaboradores em Excel", type=["xlsx", "xlsm"], key="ia_folha")

    observacoes = st.text_area("Observações adicionais para a IA")

    st.divider()
    st.markdown("### Passo 3 — Gerar parecer")

    if st.button("Gerar parecer da IA"):
        contexto = f"""
PROPOSTA SELECIONADA:
{proposta}

OBSERVAÇÕES:
{observacoes}

DRE:
{ler_excel(dre)}

BALANCETE:
{ler_excel(balancete)}

FOLHA:
{ler_excel(folha)}
"""

        try:
            with st.spinner("Gerando análise da IA..."):
                parecer = gerar_parecer_ia(contexto)

            st.success("Parecer gerado com sucesso.")
            st.markdown(parecer)

        except Exception as e:
            st.error(f"Erro ao gerar parecer da IA: {e}")


def tela_analista_ia(supabase):
    st.title("🤖 Analista IA de Precificação")

    st.info(
        "Fluxo: primeiro veja a visão geral das propostas; depois escolha uma proposta específica, anexe documentos e gere o parecer."
    )

    aba1, aba2 = st.tabs([
        "Visão Geral das Propostas",
        "Análise Individual"
    ])

    with aba1:
        tela_visao_geral(supabase)

    with aba2:
        tela_analise_individual(supabase)
