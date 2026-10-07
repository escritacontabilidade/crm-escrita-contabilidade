import streamlit as st
import pandas as pd
from datetime import datetime


MESES = {
    "Janeiro": 1,
    "Fevereiro": 2,
    "Março": 3,
    "Abril": 4,
    "Maio": 5,
    "Junho": 6,
    "Julho": 7,
    "Agosto": 8,
    "Setembro": 9,
    "Outubro": 10,
    "Novembro": 11,
    "Dezembro": 12,
}


COLUNAS_ESPERADAS = [
    "Cliente",
    "Folha de Pagamento",
    "Admissão",
    "Rescisão",
    "Contábil",
    "Entradas",
    "Saídas",
    "Processos",
    "Faturamento",
]


COLUNAS_NUMERICAS = [
    "Folha de Pagamento",
    "Admissão",
    "Rescisão",
    "Contábil",
    "Entradas",
    "Saídas",
    "Processos",
    "Faturamento",
]


def separar_codigo_cliente(valor):
    """
    Separa o código Questor da razão social.

    Exemplo:
    16 - CLINMEDI CLINICA MEDICA ITAJAI LTDA

    Retorna:
    ("16", "CLINMEDI CLINICA MEDICA ITAJAI LTDA")
    """

    if pd.isna(valor):
        return None, None

    texto = str(valor).strip()

    if not texto:
        return None, None

    if " - " not in texto:
        return None, texto

    partes = texto.split(" - ", 1)

    codigo = partes[0].strip()
    nome = partes[1].strip()

    if not codigo:
        codigo = None

    if not nome:
        nome = None

    return codigo, nome


def converter_numero(valor):
    """
    Converte valores numéricos vindos do Excel.

    Aceita números reais do Excel e também textos
    com formatação brasileira.
    """

    if pd.isna(valor):
        return 0.0

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()

    if not texto:
        return 0.0

    texto = texto.replace("R$", "").strip()

    # Formato brasileiro:
    # 1.234.567,89
    if "," in texto:
        texto = texto.replace(".", "")
        texto = texto.replace(",", ".")

    try:
        return float(texto)
    except (ValueError, TypeError):
        return 0.0


def formatar_numero(valor):
    try:
        return f"{float(valor):,.0f}".replace(",", ".")
    except Exception:
        return "0"


def formatar_moeda(valor):
    try:
        valor = float(valor)

        texto = f"{valor:,.2f}"

        texto = (
            texto
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

        return f"R$ {texto}"

    except Exception:
        return "R$ 0,00"


def preparar_arquivo_questor(arquivo):
    """
    Lê e valida o arquivo mensal exportado do Questor.

    Esta função NÃO grava dados no Supabase.
    Apenas prepara e valida os dados.
    """

    try:
        df = pd.read_excel(
            arquivo,
            sheet_name="Export",
        )
    except ValueError:
        raise ValueError(
            "Não foi encontrada a aba 'Export' no arquivo."
        )
    except Exception as erro:
        raise ValueError(
            f"Não foi possível ler o arquivo Excel: {erro}"
        )

    # ---------------------------------------------------------
    # LIMPEZA DOS NOMES DAS COLUNAS
    # ---------------------------------------------------------

    df.columns = [
        str(coluna).strip()
        for coluna in df.columns
    ]

    # ---------------------------------------------------------
    # VALIDAÇÃO DAS COLUNAS
    # ---------------------------------------------------------

    colunas_faltantes = [
        coluna
        for coluna in COLUNAS_ESPERADAS
        if coluna not in df.columns
    ]

    if colunas_faltantes:
        raise ValueError(
            "O arquivo não possui todas as colunas esperadas. "
            "Colunas ausentes: "
            + ", ".join(colunas_faltantes)
        )

    # Trabalhamos somente com as colunas que conhecemos.
    df = df[COLUNAS_ESPERADAS].copy()

    # ---------------------------------------------------------
    # REMOVER LINHAS COMPLETAMENTE VAZIAS
    # ---------------------------------------------------------

    df = df.dropna(how="all")

    # ---------------------------------------------------------
    # LIMPEZA DO CAMPO CLIENTE
    # ---------------------------------------------------------

    df["Cliente"] = df["Cliente"].astype(str).str.strip()

    # Remove linhas vazias convertidas para string.
    df = df[
        ~df["Cliente"].str.lower().isin(
            ["", "nan", "none"]
        )
    ].copy()

    # Remove linha Total.
    df = df[
        ~df["Cliente"].str.lower().str.startswith("total")
    ].copy()

    # ---------------------------------------------------------
    # SEPARAR CÓDIGO E RAZÃO SOCIAL
    # ---------------------------------------------------------

    clientes_separados = df["Cliente"].apply(
        separar_codigo_cliente
    )

    df["codigo_questor"] = clientes_separados.apply(
        lambda x: x[0]
    )

    df["razao_social"] = clientes_separados.apply(
        lambda x: x[1]
    )

    # ---------------------------------------------------------
    # MANTER SOMENTE CLIENTES COM CÓDIGO QUESTOR VÁLIDO
    # ---------------------------------------------------------

    df = df[
        df["codigo_questor"].notna()
    ].copy()

    df["codigo_questor"] = (
        df["codigo_questor"]
        .astype(str)
        .str.strip()
    )

    # O código Questor deve ser numérico.
    df = df[
        df["codigo_questor"].str.match(r"^\d+$", na=False)
    ].copy()

    # ---------------------------------------------------------
    # CONVERTER COLUNAS NUMÉRICAS
    # ---------------------------------------------------------

    for coluna in COLUNAS_NUMERICAS:
        df[coluna] = df[coluna].apply(
            converter_numero
        )

    # ---------------------------------------------------------
    # CRIAR NOTAS DE ENTRADA + SAÍDA
    # ---------------------------------------------------------

    df["notas_fiscais"] = (
        df["Entradas"]
        + df["Saídas"]
    )

    # ---------------------------------------------------------
    # REORGANIZAR COLUNAS
    # ---------------------------------------------------------

    df = df[
        [
            "codigo_questor",
            "razao_social",
            "Folha de Pagamento",
            "Admissão",
            "Rescisão",
            "Contábil",
            "Entradas",
            "Saídas",
            "notas_fiscais",
            "Processos",
            "Faturamento",
        ]
    ].copy()

    # ---------------------------------------------------------
    # RENOMEAR PARA NOMES INTERNOS
    # ---------------------------------------------------------

    df = df.rename(
        columns={
            "Folha de Pagamento": "folha_pagamento",
            "Admissão": "admissoes",
            "Rescisão": "rescisoes",
            "Contábil": "contabil",
            "Entradas": "entradas",
            "Saídas": "saidas",
            "Processos": "processos",
            "Faturamento": "faturamento",
        }
    )

    # ---------------------------------------------------------
    # REMOVER POSSÍVEIS DUPLICIDADES DO MESMO CÓDIGO
    # ---------------------------------------------------------

    df = df.drop_duplicates(
        subset=["codigo_questor"],
        keep="last",
    )

    df = df.reset_index(drop=True)

    return df


def tela_monitoramento_producao(supabase):

    st.title("📊 Monitoramento de Produção")

    st.write(
        "Importação e acompanhamento da movimentação mensal "
        "dos clientes da Escrita Contabilidade."
    )

    st.divider()

    st.subheader("Importar produção do Questor")

    st.info(
        "Informe a competência correspondente aos dados do arquivo. "
        "Exemplo: se o arquivo contém a produção de setembro de 2026, "
        "selecione Setembro e 2026, mesmo que a importação esteja sendo "
        "realizada em outubro."
    )

    # =========================================================
    # COMPETÊNCIA
    # =========================================================

    col_mes, col_ano = st.columns(2)

    with col_mes:

        mes_nome = st.selectbox(
            "Mês da competência *",
            options=list(MESES.keys()),
            index=datetime.now().month - 1,
            key="producao_mes_competencia",
        )

    with col_ano:

        ano_atual = datetime.now().year

        anos = list(
            range(
                ano_atual - 5,
                ano_atual + 2,
            )
        )

        ano = st.selectbox(
            "Ano da competência *",
            options=anos,
            index=anos.index(ano_atual),
            key="producao_ano_competencia",
        )

    mes_numero = MESES[mes_nome]

    competencia = (
        f"{ano}-{mes_numero:02d}-01"
    )

    st.caption(
        f"Competência selecionada: "
        f"**{mes_nome}/{ano}**"
    )

    # =========================================================
    # SISTEMA
    # =========================================================

    st.text_input(
        "Sistema de origem",
        value="Questor",
        disabled=True,
        key="producao_sistema_origem",
    )

    # =========================================================
    # ARQUIVO
    # =========================================================

    arquivo = st.file_uploader(
        "Arquivo de produção do Questor *",
        type=["xlsx", "xls"],
        key="arquivo_producao_questor",
        help=(
            "Selecione o arquivo mensal "
            "exportado do Questor."
        ),
    )

    if arquivo is None:

        st.warning(
            "Selecione o arquivo correspondente "
            "à competência informada."
        )

        return

    # =========================================================
    # IDENTIFICAÇÃO
    # =========================================================

    st.success("Arquivo selecionado.")

    st.write(
        f"**Arquivo:** {arquivo.name}"
    )

    st.write(
        "**Sistema:** Questor"
    )

    st.write(
        f"**Competência:** {mes_nome}/{ano}"
    )

    st.divider()

    # =========================================================
    # LEITURA E VALIDAÇÃO
    # =========================================================

    st.subheader("Validação do arquivo")

    try:

        df = preparar_arquivo_questor(
            arquivo
        )

    except Exception as erro:

        st.error(
            f"Erro ao validar o arquivo: {erro}"
        )

        return

    if df.empty:

        st.error(
            "Nenhum cliente válido foi encontrado "
            "no arquivo."
        )

        return

    st.success(
        "Arquivo validado com sucesso. "
        "Nenhum dado foi gravado no banco de dados."
    )

    # =========================================================
    # INDICADORES GERAIS
    # =========================================================

    st.subheader("Resumo da produção")

    quantidade_clientes = len(df)

    total_folha = df[
        "folha_pagamento"
    ].sum()

    total_processos = df[
        "processos"
    ].sum()

    total_faturamento = df[
        "faturamento"
    ].sum()

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Clientes",
            formatar_numero(
                quantidade_clientes
            ),
        )

    with col2:

        st.metric(
            "Folha de pagamento",
            formatar_numero(
                total_folha
            ),
        )

    with col3:

        st.metric(
            "Processos",
            formatar_numero(
                total_processos
            ),
        )

    with col4:

        st.metric(
            "Faturamento",
            formatar_moeda(
                total_faturamento
            ),
        )

    # =========================================================
    # DEMAIS INDICADORES
    # =========================================================

    st.markdown(
        "#### Demais movimentações"
    )

    total_admissoes = df[
        "admissoes"
    ].sum()

    total_rescisoes = df[
        "rescisoes"
    ].sum()

    total_contabil = df[
        "contabil"
    ].sum()

    total_entradas = df[
        "entradas"
    ].sum()

    total_saidas = df[
        "saidas"
    ].sum()

    total_notas = df[
        "notas_fiscais"
    ].sum()

    col5, col6, col7 = st.columns(3)

    with col5:

        st.metric(
            "Admissões",
            formatar_numero(
                total_admissoes
            ),
        )

        st.metric(
            "Entradas",
            formatar_numero(
                total_entradas
            ),
        )

    with col6:

        st.metric(
            "Rescisões",
            formatar_numero(
                total_rescisoes
            ),
        )

        st.metric(
            "Saídas",
            formatar_numero(
                total_saidas
            ),
        )

    with col7:

        st.metric(
            "Lançamentos contábeis",
            formatar_numero(
                total_contabil
            ),
        )

        st.metric(
            "Notas fiscais",
            formatar_numero(
                total_notas
            ),
        )

    st.divider()

    # =========================================================
    # PRÉ-VISUALIZAÇÃO
    # =========================================================

    st.subheader(
        "Pré-visualização dos clientes"
    )

    st.caption(
        "A tabela abaixo mostra como os dados serão "
        "tratados antes da futura importação."
    )

    df_visualizacao = df.copy()

    df_visualizacao = df_visualizacao.rename(
        columns={
            "codigo_questor": "Código Questor",
            "razao_social": "Cliente",
            "folha_pagamento": "Folha",
            "admissoes": "Admissões",
            "rescisoes": "Rescisões",
            "contabil": "Contábil",
            "entradas": "Entradas",
            "saidas": "Saídas",
            "notas_fiscais": "Notas",
            "processos": "Processos",
            "faturamento": "Faturamento",
        }
    )

    st.dataframe(
        df_visualizacao,
        use_container_width=True,
        hide_index=True,
    )

    # =========================================================
    # INFORMAÇÕES PARA FUTURA GRAVAÇÃO
    # =========================================================

    st.divider()

    st.subheader(
        "Dados preparados para importação"
    )

    st.write(
        f"**Sistema:** Questor"
    )

    st.write(
        f"**Competência:** {competencia}"
    )

    st.write(
        f"**Clientes válidos:** "
        f"{quantidade_clientes}"
    )

    st.write(
        "**Identificador principal:** "
        "Código Questor"
    )

    st.write(
        "**Notas fiscais:** "
        "Entradas + Saídas"
    )

    st.warning(
        "Nesta etapa os dados ainda NÃO serão gravados "
        "no Supabase. Estamos validando a leitura e o "
        "tratamento do arquivo antes de habilitar a "
        "importação definitiva."
    )
