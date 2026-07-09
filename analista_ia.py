import re
import pandas as pd
import streamlit as st
import google.generativeai as genai
import fitz


def formatar_brl(valor):
    try:
        return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def converter_numero(valor):
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()
    texto = texto.replace("R$", "").replace(" ", "")
    texto = texto.replace(".", "").replace(",", ".")

    try:
        return float(texto)
    except Exception:
        return None


def preparar_dataframe(df):
    df = df.copy()

    for col in df.columns:
        if df[col].dtype == "object":
            convertido = df[col].apply(converter_numero)
            taxa_validos = convertido.notna().mean()

            if taxa_validos >= 0.60:
                df[col] = convertido

    return df


def resumir_dataframe(df, nome_arquivo, limite_colunas=12):
    if df is None or df.empty:
        return f"{nome_arquivo}: arquivo vazio ou sem dados legíveis."

    df = preparar_dataframe(df)

    resumo = []
    resumo.append(f"ARQUIVO: {nome_arquivo}")
    resumo.append(f"Linhas: {len(df)}")
    resumo.append(f"Colunas: {len(df.columns)}")
    resumo.append(f"Colunas identificadas: {list(df.columns)[:25]}")

    numericas = df.select_dtypes(include="number").columns.tolist()

    if numericas:
        resumo.append("INDICADORES NUMÉRICOS:")
        for col in numericas[:limite_colunas]:
            serie = df[col].dropna()
            if not serie.empty:
                resumo.append(
                    f"- {col}: soma={serie.sum():.2f}; média={serie.mean():.2f}; "
                    f"mín={serie.min():.2f}; máx={serie.max():.2f}"
                )

    colunas_texto_importantes = [
        c for c in df.columns
        if any(p in str(c).lower() for p in ["cliente", "empresa", "cargo", "regime", "tribut", "status", "situação", "situacao"])
    ]

    if colunas_texto_importantes:
        resumo.append("PRINCIPAIS CATEGORIAS:")
        for col in colunas_texto_importantes[:6]:
            contagem = df[col].astype(str).value_counts().head(8)
            resumo.append(f"- {col}: {contagem.to_dict()}")

    return "\n".join(resumo)


def ler_excel_indicadores(uploaded_file, nome_arquivo):
    if uploaded_file is None:
        return f"{nome_arquivo}: arquivo não enviado."

    try:
        abas = pd.read_excel(uploaded_file, sheet_name=None)
        partes = []

        for nome_aba, df in abas.items():
            partes.append(f"\nABA: {nome_aba}")
            partes.append(resumir_dataframe(df, nome_arquivo))

        return "\n".join(partes)

    except Exception as e:
        return f"{nome_arquivo}: erro ao ler Excel: {e}"


def ler_pdf_indicadores(uploaded_file, nome_arquivo, max_paginas=20):
    if uploaded_file is None:
        return f"{nome_arquivo}: arquivo não enviado."

    try:
        pdf_bytes = uploaded_file.getvalue()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        linhas_relevantes = []
        termos = [
            "RECEITAS TOTAIS",
            "DESPESAS TOTAIS",
            "LUCRO FINAL",
            "Sub Total",
            "Vl. Recebido",
            "Vl. Doc",
            "Cliente",
            "Período",
        ]

        for i, page in enumerate(doc):
            if i >= max_paginas:
                break

            texto = page.get_text("text")
            for linha in texto.splitlines():
                if any(t.lower() in linha.lower() for t in termos):
                    linhas_relevantes.append(linha.strip())

        linhas_relevantes = linhas_relevantes[:120]

        return f"""
ARQUIVO: {nome_arquivo}
Páginas totais: {len(doc)}
Páginas analisadas: {min(len(doc), max_paginas)}
Linhas relevantes extraídas:
{chr(10).join(linhas_relevantes)}
"""

    except Exception as e:
        return f"{nome_arquivo}: erro ao ler PDF: {e}"


def extrair_linha(texto, titulo):
    padrao = rf"{titulo}\s*[:\-]?\s*(.+)"
    achou = re.search(padrao, texto, re.IGNORECASE)
    if achou:
        return achou.group(1).strip()
    return "Não identificado"


def gerar_parecer_ia(contexto):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3-flash-preview")

    prompt = f"""
Você é um analista sênior de precificação contábil, controller e consultor empresarial.

Analise somente os INDICADORES RESUMIDOS abaixo.
Não invente dados.
Não use balancete.
Não peça documentos diferentes.
Não diga que analisou arquivo bruto; você recebeu indicadores extraídos dos arquivos enviados.

CONTEXTO COMPACTADO:
{contexto}

Responda obrigatoriamente neste formato:

RESUMO_EXECUTIVO: síntese objetiva em até 5 linhas.
PRECO_MINIMO: preço mínimo recomendado ou "Não identificado".
PRECO_IDEAL: preço ideal recomendado ou "Não identificado".
NOTA_OPORTUNIDADE: apenas A, B, C ou D.
RISCO: apenas Baixo, Médio ou Alto.

Depois detalhe:

1. Diagnóstico executivo
2. Análise da proposta selecionada
3. Análise do faturamento histórico
4. Análise das contas recebidas
5. Análise da DRE Financeira
6. Análise da folha por empresa
7. Comparação com Tabela Honorários (2).xls
8. Impacto de Valores retraballho (3).xlsx
9. Riscos operacionais
10. Preço mínimo recomendado
11. Preço ideal recomendado
12. Nota da oportunidade
13. Recomendação comercial final
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


def aplicar_estilo():
    st.markdown("""
    <style>
    .ia-card {
        padding: 22px;
        border-radius: 14px;
        color: #111827;
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        min-height: 125px;
    }
    .ia-card h4 {
        margin: 0;
        font-size: 14px;
        color: #475569;
        font-weight: 600;
    }
    .ia-card h2 {
        margin-top: 12px;
        font-size: 22px;
        color: #0f172a;
    }
    .card-green { background: #dcfce7; border-color: #86efac; }
    .card-yellow { background: #fef9c3; border-color: #fde047; }
    .card-red { background: #fee2e2; border-color: #fca5a5; }
    .card-blue { background: #dbeafe; border-color: #93c5fd; }
    .parecer-box {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 26px;
        line-height: 1.65;
        color: #111827;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    }
    .resumo-box {
        background: #f8fafc;
        border-left: 6px solid #1d4ed8;
        padding: 18px 22px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)


def renderizar_painel_ia(parecer):
    resumo = extrair_linha(parecer, "RESUMO_EXECUTIVO")
    preco_minimo = extrair_linha(parecer, "PRECO_MINIMO")
    preco_ideal = extrair_linha(parecer, "PRECO_IDEAL")
    nota = extrair_linha(parecer, "NOTA_OPORTUNIDADE")
    risco = extrair_linha(parecer, "RISCO")

    risco_normalizado = str(risco).lower()

    if "alto" in risco_normalizado:
        classe_risco = "card-red"
    elif "médio" in risco_normalizado or "medio" in risco_normalizado:
        classe_risco = "card-yellow"
    else:
        classe_risco = "card-green"

    st.markdown("## Painel Executivo da IA")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f'<div class="ia-card card-blue"><h4>Preço mínimo</h4><h2>{preco_minimo}</h2></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="ia-card card-green"><h4>Preço ideal</h4><h2>{preco_ideal}</h2></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="ia-card card-yellow"><h4>Nota da oportunidade</h4><h2>{nota}</h2></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="ia-card {classe_risco}"><h4>Risco</h4><h2>{risco}</h2></div>', unsafe_allow_html=True)

    st.divider()

    st.markdown("### Resumo executivo")
    st.markdown(f'<div class="resumo-box">{resumo}</div>', unsafe_allow_html=True)

    texto_limpo = parecer
    for campo in ["RESUMO_EXECUTIVO", "PRECO_MINIMO", "PRECO_IDEAL", "NOTA_OPORTUNIDADE", "RISCO"]:
        texto_limpo = re.sub(rf"{campo}\s*[:\-]?\s*.+", "", texto_limpo, flags=re.IGNORECASE)

    st.markdown("### Parecer completo")
    st.markdown(f'<div class="parecer-box">{texto_limpo}</div>', unsafe_allow_html=True)


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
        lambda row: (
            (float(row.get("valor_final") or 0) - float(row.get("valor_calculado") or 0))
            / float(row.get("valor_calculado") or 1)
        ) * 100 if float(row.get("valor_calculado") or 0) > 0 else 0,
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
    st.markdown("### Passo 2 — Anexe exatamente estes arquivos")

    arquivo_faturamento_xlsx = st.file_uploader("1-Relatorio e faturamento ultimos 12 meses .xlsx", type=["xlsx"], key="ia_faturamento_xlsx")
    arquivo_contas_xlsx = st.file_uploader("2-Relatorio de contas recebida ultimos 12 meses.xlsx", type=["xlsx"], key="ia_contas_xlsx")
    arquivo_dre_pdf = st.file_uploader("DRE Financeiro.pdf", type=["pdf"], key="ia_dre_pdf")
    arquivo_dre_xlsx = st.file_uploader("DRE Financeiro.xlsx", type=["xlsx"], key="ia_dre_xlsx")
    arquivo_funcionarios = st.file_uploader("Funcionários Cargo Salário por Empresa.xlsx", type=["xlsx"], key="ia_funcionarios")
    arquivo_plano = st.file_uploader("Plano de Contas Financeiro.xlsx", type=["xlsx"], key="ia_plano")
    arquivo_contas_pdf = st.file_uploader("Relatório de contas recebidas ultimos 12 meses.pdf", type=["pdf"], key="ia_contas_pdf")
    arquivo_faturamento_pdf = st.file_uploader("Relatório de Faturamento ultimos 12 meses.pdf", type=["pdf"], key="ia_faturamento_pdf")
    arquivo_honorarios = st.file_uploader("Tabela Honorários (2).xls", type=["xls"], key="ia_honorarios")
    arquivo_retrabalho = st.file_uploader("Valores retraballho (3).xlsx", type=["xlsx"], key="ia_retrabalho")

    observacoes = st.text_area("Observações adicionais para a IA")

    st.divider()
    st.markdown("### Passo 3 — Gerar parecer")

    if st.button("Gerar parecer da IA"):
        contexto = f"""
PROPOSTA SELECIONADA:
{proposta}

OBSERVAÇÕES:
{observacoes}

INDICADORES EXTRAÍDOS DOS ARQUIVOS:

{ler_excel_indicadores(arquivo_faturamento_xlsx, "1-Relatorio e faturamento ultimos 12 meses .xlsx")}

{ler_excel_indicadores(arquivo_contas_xlsx, "2-Relatorio de contas recebida ultimos 12 meses.xlsx")}

{ler_pdf_indicadores(arquivo_dre_pdf, "DRE Financeiro.pdf")}

{ler_excel_indicadores(arquivo_dre_xlsx, "DRE Financeiro.xlsx")}

{ler_excel_indicadores(arquivo_funcionarios, "Funcionários Cargo Salário por Empresa.xlsx")}

{ler_excel_indicadores(arquivo_plano, "Plano de Contas Financeiro.xlsx")}

{ler_pdf_indicadores(arquivo_contas_pdf, "Relatório de contas recebidas ultimos 12 meses.pdf")}

{ler_pdf_indicadores(arquivo_faturamento_pdf, "Relatório de Faturamento ultimos 12 meses.pdf")}

{ler_excel_indicadores(arquivo_honorarios, "Tabela Honorários (2).xls")}

{ler_excel_indicadores(arquivo_retrabalho, "Valores retraballho (3).xlsx")}
"""

        try:
            with st.spinner("Processando indicadores e gerando análise da IA..."):
                parecer = gerar_parecer_ia(contexto)

            st.success("Parecer gerado com sucesso.")
            renderizar_painel_ia(parecer)

            with st.expander("Ver contexto resumido enviado para IA"):
                st.text(contexto)

            with st.expander("Ver resposta bruta da IA"):
                st.text(parecer)

        except Exception as e:
            st.error(f"Erro ao gerar parecer da IA: {e}")


def tela_analista_ia(supabase):
    aplicar_estilo()

    st.title("🤖 Analista IA de Precificação")

    st.info(
        "Fluxo: veja a visão geral das propostas, escolha uma proposta, anexe os arquivos oficiais e gere uma análise baseada em indicadores compactos."
    )

    aba1, aba2 = st.tabs([
        "Visão Geral das Propostas",
        "Análise Individual"
    ])

    with aba1:
        tela_visao_geral(supabase)

    with aba2:
        tela_analise_individual(supabase)
