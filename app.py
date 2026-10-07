import streamlit as st
import pandas as pd
import re
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


COLUNAS_OBRIGATORIAS = [
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
    Separa o código Questor do nome do cliente.

    Exemplo:
    111 - EMPRESA TESTE LTDA

    Retorna:
    ("111", "EMPRESA TESTE LTDA")
    """

    if pd.isna(valor):
        return None, None

    texto = str(valor).strip()

    if not texto:
        return None, None

    partes = re.match(r"^\s*(\d+)\s*-\s*(.+?)\s*$", texto)

    if not partes:
        return None, texto

    codigo = partes.group(1).strip()
    nome = partes.group(2).strip()

    return codigo, nome


def calcular_notas_fiscais(linha):
    """
    Calcula Entradas + Saídas.

    IMPORTANTE:
    - Se os dois campos estiverem vazios, mantém vazio.
    - Se apenas um estiver preenchido, utiliza o valor existente.
    """

    entrada = linha.get("Entradas")
    saida = linha.get("Saídas")

    entrada_vazia = pd.isna(entrada)
    saida_vazia = pd.isna(saida)

    if entrada_vazia and saida_vazia:
        return None

    entrada_valor = 0 if entrada_vazia else float(entrada)
    saida_valor = 0 if saida_vazia else float(saida)

    return entrada_valor + saida_valor


def preparar_arquivo_questor(arquivo):
    """
    Lê e valida o arquivo mensal exportado do Questor.
    """

    df = pd.read_excel(arquivo)

    # Remove espaços extras dos nomes das colunas
    df.columns = [str(c).strip() for c in df.columns]

    # ---------------------------------------------------------
    # VALIDAR ESTRUTURA
    # ---------------------------------------------------------

    colunas_ausentes = [
        coluna
        for coluna in COLUNAS_OBRIGATORIAS
        if coluna not in df.columns
    ]

    if colunas_ausentes:
        raise ValueError(
            "O arquivo não possui todas as colunas esperadas. "
            f"Colunas ausentes: {', '.join(colunas_ausentes)}"
        )

    # Trabalha somente com as colunas conhecidas
    df = df[COLUNAS_OBRIGATORIAS].copy()

    # ---------------------------------------------------------
    # REMOVER LINHAS TOTALMENTE VAZIAS
    # ---------------------------------------------------------

    df = df.dropna(how="all")

    # Remove linha sem cliente
    df = df[
        df["Cliente"].notna()
        & (df["Cliente"].astype(str).str.strip() != "")
    ].copy()

    # ---------------------------------------------------------
    # CONVERTER CAMPOS NUMÉRICOS
    # ---------------------------------------------------------

    for coluna in COLUNAS_NUMERICAS:
        df[coluna] = pd.to_numeric(
            df[coluna],
            errors="coerce"
        )

    # ---------------------------------------------------------
    # SEPARAR CÓDIGO E NOME
    # ---------------------------------------------------------

    resultado_clientes = df["Cliente"].apply(
        separar_codigo_cliente
    )

    df["Código Questor"] = resultado_clientes.apply(
        lambda x: x[0]
    )

    df["Nome do Cliente"] = resultado_clientes.apply(
        lambda x: x[1]
    )

    # ---------------------------------------------------------
    # CALCULAR TOTAL DE NOTAS FISCAIS
    # ---------------------------------------------------------

    df["Notas Fiscais"] = df.apply(
        calcular_notas_fiscais,
        axis=1
    )

    # ---------------------------------------------------------
    # ORDENAR COLUNAS PARA VISUALIZAÇÃO
    # ---------------------------------------------------------

    colunas_saida = [
        "Código Questor",
        "Nome do Cliente",
        "Folha de Pagamento",
        "Admissão",
        "Rescisão",
        "Contábil",
        "Entradas",
        "Saídas",
        "Notas Fiscais",
        "Processos",
        "Faturamento",
    ]

    return df[colunas_saida].copy()


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
        "selecione Setembro e 2026, mesmo que a importação esteja "
        "sendo realizada em outubro."
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
                ano_atual + 2
            )
        )

        ano = st.selectbox(
            "Ano da competência *",
            options=anos,
            index=anos.index(ano_atual),
            key="producao_ano_competencia",
        )

    mes_numero = MESES[mes_nome]

    competencia = f"{ano}-{mes_numero:02d}-01"

    st.caption(
        f"Competência selecionada: **{mes_nome}/{ano}**"
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
        help="Selecione o arquivo mensal exportado do Questor.",
    )

    if arquivo is None:
        st.warning(
            "Selecione o arquivo correspondente à competência informada."
        )
        return

    # =========================================================
    # LER E VALIDAR ARQUIVO
    # =========================================================

    try:
        df = preparar_arquivo_questor(arquivo)

    except Exception as e:
        st.error(
            "Não foi possível validar o arquivo."
        )

        st.exception(e)

        return

    st.success(
        "Arquivo lido e estrutura validada com sucesso."
    )

    # =========================================================
    # RESUMO
    # =========================================================

    st.subheader("Resumo da importação")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Clientes encontrados",
            len(df)
        )

    with col2:
        clientes_codigo = int(
            df["Código Questor"].notna().sum()
        )

        st.metric(
            "Com código Questor",
            clientes_codigo
        )

    with col3:
        sem_codigo = int(
            df["Código Questor"].isna().sum()
        )

        st.metric(
            "Sem código",
            sem_codigo
        )

    with col4:
        st.metric(
            "Competência",
            f"{mes_numero:02d}/{ano}"
        )

    st.caption(
        f"Arquivo: {arquivo.name} | "
        f"Sistema: Questor | "
        f"Competência: {mes_nome}/{ano}"
    )

    # =========================================================
    # VALIDAÇÃO DE CÓDIGOS
    # =========================================================

    registros_sem_codigo = df[
        df["Código Questor"].isna()
    ]

    if len(registros_sem_codigo) > 0:

        st.warning(
            f"Foram encontrados {len(registros_sem_codigo)} "
            "registros sem código Questor identificável."
        )

        with st.expander(
            "Ver registros sem código"
        ):
            st.dataframe(
                registros_sem_codigo,
                use_container_width=True,
                hide_index=True,
            )

    else:
        st.success(
            "Todos os clientes possuem código Questor identificável."
        )

    # =========================================================
    # INDICADORES DISPONÍVEIS
    # =========================================================

    st.subheader("Indicadores encontrados")

    indicadores = pd.DataFrame({
        "Indicador": [
            "Folha de Pagamento",
            "Admissão",
            "Rescisão",
            "Contábil",
            "Entradas",
            "Saídas",
            "Notas Fiscais",
            "Processos",
            "Faturamento",
        ],
        "Registros com informação": [
            int(df["Folha de Pagamento"].notna().sum()),
            int(df["Admissão"].notna().sum()),
            int(df["Rescisão"].notna().sum()),
            int(df["Contábil"].notna().sum()),
            int(df["Entradas"].notna().sum()),
            int(df["Saídas"].notna().sum()),
            int(df["Notas Fiscais"].notna().sum()),
            int(df["Processos"].notna().sum()),
            int(df["Faturamento"].notna().sum()),
        ],
        "Uso inicial": [
            "Análise principal",
            "Histórico",
            "Histórico",
            "Histórico",
            "Composição Notas Fiscais",
            "Composição Notas Fiscais",
            "Histórico",
            "Análise principal",
            "Análise principal",
        ],
    })

    st.dataframe(
        indicadores,
        use_container_width=True,
        hide_index=True,
    )

    # =========================================================
    # PRÉVIA
    # =========================================================

    st.subheader("Prévia dos dados")

    st.write(
        "Confira os dados abaixo antes de habilitarmos "
        "a gravação no banco."
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    # =========================================================
    # OBSERVAÇÃO SOBRE CAMPOS VAZIOS
    # =========================================================

    st.info(
        "Campos vazios no arquivo do Questor estão sendo mantidos "
        "como ausência de informação. Eles não serão convertidos "
        "automaticamente para zero."
    )

    # =========================================================
    # IMPORTAÇÃO AINDA BLOQUEADA
    # =========================================================

    st.divider()

    st.warning(
        "A gravação no banco de dados continua bloqueada nesta etapa. "
        "Depois de validarmos esta prévia, habilitaremos a importação."
    )
