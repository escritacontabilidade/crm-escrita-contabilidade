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


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def separar_codigo_cliente(valor):
    """
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
    Converte valores numéricos do Excel.
    Aceita número real e texto em padrão brasileiro.
    """

    if pd.isna(valor):
        return 0.0

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()

    if not texto:
        return 0.0

    texto = texto.replace("R$", "").strip()

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


# ============================================================
# LEITURA E TRATAMENTO DO EXCEL
# ============================================================

def preparar_arquivo_questor(arquivo):

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

    # --------------------------------------------------------
    # LIMPAR NOMES DAS COLUNAS
    # --------------------------------------------------------

    df.columns = [
        str(coluna).strip()
        for coluna in df.columns
    ]

    # --------------------------------------------------------
    # VALIDAR COLUNAS
    # --------------------------------------------------------

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

    df = df[COLUNAS_ESPERADAS].copy()

    # --------------------------------------------------------
    # REMOVER LINHAS VAZIAS
    # --------------------------------------------------------

    df = df.dropna(how="all")

    df["Cliente"] = (
        df["Cliente"]
        .astype(str)
        .str.strip()
    )

    df = df[
        ~df["Cliente"]
        .str.lower()
        .isin(["", "nan", "none"])
    ].copy()

    # --------------------------------------------------------
    # REMOVER TOTAL
    # --------------------------------------------------------

    df = df[
        ~df["Cliente"]
        .str.lower()
        .str.startswith("total")
    ].copy()

    # --------------------------------------------------------
    # SEPARAR CÓDIGO E NOME
    # --------------------------------------------------------

    clientes_separados = df["Cliente"].apply(
        separar_codigo_cliente
    )

    df["codigo_questor"] = clientes_separados.apply(
        lambda x: x[0]
    )

    df["razao_social"] = clientes_separados.apply(
        lambda x: x[1]
    )

    # --------------------------------------------------------
    # VALIDAR CÓDIGO QUESTOR
    # --------------------------------------------------------

    df = df[
        df["codigo_questor"].notna()
    ].copy()

    df["codigo_questor"] = (
        df["codigo_questor"]
        .astype(str)
        .str.strip()
    )

    df = df[
        df["codigo_questor"]
        .str.match(r"^\d+$", na=False)
    ].copy()

    # --------------------------------------------------------
    # CONVERTER NÚMEROS
    # --------------------------------------------------------

    for coluna in COLUNAS_NUMERICAS:
        df[coluna] = df[coluna].apply(
            converter_numero
        )

    # --------------------------------------------------------
    # NOTAS FISCAIS
    # --------------------------------------------------------

    df["notas_fiscais"] = (
        df["Entradas"]
        + df["Saídas"]
    )

    # --------------------------------------------------------
    # REORGANIZAR
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # NOMES INTERNOS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # EVITAR CÓDIGO DUPLICADO NO MESMO ARQUIVO
    # --------------------------------------------------------

    df = df.drop_duplicates(
        subset=["codigo_questor"],
        keep="last",
    )

    return df.reset_index(drop=True)


# ============================================================
# BANCO DE DADOS
# ============================================================

def contar_registros_competencia(
    supabase,
    sistema,
    competencia,
):
    """
    Retorna quantos registros já existem para
    sistema + competência.
    """

    resultado = (
        supabase
        .table("producao_clientes")
        .select("id", count="exact")
        .eq("sistema", sistema)
        .eq("competencia", competencia)
        .execute()
    )

    return resultado.count or 0


def preparar_registros_banco(
    df,
    competencia,
    arquivo_nome,
):
    """
    Converte o DataFrame validado em registros
    compatíveis com producao_clientes.
    """

    registros = []

    for _, linha in df.iterrows():

        registro = {
            "sistema": "Questor",
            "codigo_cliente": str(
                linha["codigo_questor"]
            ),
            "cliente": str(
                linha["razao_social"]
            ),
            "competencia": competencia,

            "folha_pagamento": float(
                linha["folha_pagamento"]
            ),

            "admissao": float(
                linha["admissoes"]
            ),

            "rescisao": float(
                linha["rescisoes"]
            ),

            "contabil": float(
                linha["contabil"]
            ),

            "entradas": float(
                linha["entradas"]
            ),

            "saidas": float(
                linha["saidas"]
            ),

            "notas_fiscais": float(
                linha["notas_fiscais"]
            ),

            "processos": float(
                linha["processos"]
            ),

            "faturamento": float(
                linha["faturamento"]
            ),

            "arquivo_origem": arquivo_nome,
        }

        registros.append(registro)

    return registros


def inserir_registros_em_lotes(
    supabase,
    registros,
    tamanho_lote=100,
):
    """
    Insere os registros em pequenos lotes.
    Isso evita enviar centenas de linhas em
    uma única requisição.
    """

    total_inseridos = 0

    for inicio in range(
        0,
        len(registros),
        tamanho_lote,
    ):

        lote = registros[
            inicio:inicio + tamanho_lote
        ]

        resultado = (
            supabase
            .table("producao_clientes")
            .insert(lote)
            .execute()
        )

        if resultado.data:
            total_inseridos += len(
                resultado.data
            )
        else:
            total_inseridos += len(lote)

    return total_inseridos


def excluir_competencia(
    supabase,
    sistema,
    competencia,
):
    """
    Exclui somente a competência informada
    para o sistema informado.
    """

    return (
        supabase
        .table("producao_clientes")
        .delete()
        .eq("sistema", sistema)
        .eq("competencia", competencia)
        .execute()
    )


# ============================================================
# HISTÓRICO DE IMPORTAÇÕES
# ============================================================

def buscar_historico_importacoes(supabase, sistema="Questor"):
    """
    Busca todos os registros de produção do sistema informado,
    usando paginação para não ficar limitado aos primeiros 1.000 registros,
    e consolida os totais por competência.
    """
    campos = (
        "competencia,codigo_cliente,folha_pagamento,"
        "admissao,rescisao,contabil,entradas,saidas,"
        "notas_fiscais,processos,faturamento"
    )

    todos_registros = []
    inicio = 0
    tamanho_pagina = 1000

    while True:
        resultado = (
            supabase
            .table("producao_clientes")
            .select(campos)
            .eq("sistema", sistema)
            .order("competencia", desc=True)
            .range(inicio, inicio + tamanho_pagina - 1)
            .execute()
        )

        lote = resultado.data or []
        todos_registros.extend(lote)

        if len(lote) < tamanho_pagina:
            break

        inicio += tamanho_pagina

    if not todos_registros:
        return pd.DataFrame()

    df_hist = pd.DataFrame(todos_registros)

    colunas_numericas = [
        "folha_pagamento",
        "admissao",
        "rescisao",
        "contabil",
        "entradas",
        "saidas",
        "notas_fiscais",
        "processos",
        "faturamento",
    ]

    for coluna in colunas_numericas:
        df_hist[coluna] = pd.to_numeric(
            df_hist[coluna],
            errors="coerce",
        ).fillna(0)

    df_hist["competencia"] = pd.to_datetime(
        df_hist["competencia"],
        errors="coerce",
    )

    df_hist = df_hist.dropna(subset=["competencia"])

    historico = (
        df_hist
        .groupby("competencia", as_index=False)
        .agg(
            clientes=("codigo_cliente", "nunique"),
            folha_pagamento=("folha_pagamento", "sum"),
            admissao=("admissao", "sum"),
            rescisao=("rescisao", "sum"),
            contabil=("contabil", "sum"),
            entradas=("entradas", "sum"),
            saidas=("saidas", "sum"),
            notas_fiscais=("notas_fiscais", "sum"),
            processos=("processos", "sum"),
            faturamento=("faturamento", "sum"),
        )
        .sort_values("competencia", ascending=False)
        .reset_index(drop=True)
    )

    return historico


def exibir_historico_importacoes(supabase):
    st.subheader("Histórico de Importações")

    try:
        historico = buscar_historico_importacoes(
            supabase,
            "Questor",
        )
    except Exception as erro:
        st.error(
            "Não foi possível carregar o histórico de importações."
        )
        st.exception(erro)
        return

    if historico.empty:
        st.info(
            "Ainda não existem competências do Questor "
            "importadas no banco de dados."
        )
        return

    nomes_meses = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro",
    }

    visual = historico.copy()

    visual["Competência"] = visual["competencia"].apply(
        lambda data: f"{nomes_meses[data.month]}/{data.year}"
    )

    visual["Clientes"] = visual["clientes"].apply(formatar_numero)
    visual["Folha"] = visual["folha_pagamento"].apply(formatar_numero)
    visual["Admissões"] = visual["admissao"].apply(formatar_numero)
    visual["Rescisões"] = visual["rescisao"].apply(formatar_numero)
    visual["Contábil"] = visual["contabil"].apply(formatar_numero)
    visual["Entradas"] = visual["entradas"].apply(formatar_numero)
    visual["Saídas"] = visual["saidas"].apply(formatar_numero)
    visual["Notas Fiscais"] = visual["notas_fiscais"].apply(formatar_numero)
    visual["Processos"] = visual["processos"].apply(formatar_numero)
    visual["Faturamento"] = visual["faturamento"].apply(formatar_moeda)

    visual = visual[
        [
            "Competência",
            "Clientes",
            "Folha",
            "Admissões",
            "Rescisões",
            "Contábil",
            "Entradas",
            "Saídas",
            "Notas Fiscais",
            "Processos",
            "Faturamento",
        ]
    ]

    st.dataframe(
        visual,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        f"{len(visual)} competência(s) importada(s) do Questor."
    )


# ============================================================
# TELA
# ============================================================

def tela_monitoramento_producao(supabase):

    st.title("📊 Monitoramento de Produção")

    st.write(
        "Importação e acompanhamento da movimentação mensal "
        "dos clientes da Escrita Contabilidade."
    )

    st.divider()

    # ========================================================
    # HISTÓRICO DE IMPORTAÇÕES
    # ========================================================

    exibir_historico_importacoes(supabase)

    st.divider()

    st.subheader("Importar produção do Questor")

    st.info(
        "Informe a competência correspondente aos dados do arquivo. "
        "Exemplo: se o arquivo contém a produção de setembro de 2026, "
        "selecione Setembro e 2026, mesmo que a importação esteja "
        "sendo realizada em outubro."
    )

    # ========================================================
    # COMPETÊNCIA
    # ========================================================

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

    # ========================================================
    # SISTEMA
    # ========================================================

    st.text_input(
        "Sistema de origem",
        value="Questor",
        disabled=True,
        key="producao_sistema_origem",
    )

    # ========================================================
    # ARQUIVO
    # ========================================================

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

    # ========================================================
    # VALIDAÇÃO
    # ========================================================

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
            "Nenhum cliente válido foi encontrado."
        )

        return

    st.success(
        "Arquivo validado com sucesso."
    )

    # ========================================================
    # INDICADORES
    # ========================================================

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

    # ========================================================
    # DEMAIS MOVIMENTAÇÕES
    # ========================================================

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

    # ========================================================
    # PRÉ-VISUALIZAÇÃO
    # ========================================================

    st.subheader(
        "Pré-visualização dos clientes"
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

    st.divider()

    # ========================================================
    # VERIFICAR SE A COMPETÊNCIA JÁ EXISTE
    # ========================================================

    st.subheader("Importação para o banco de dados")

    try:

        registros_existentes = (
            contar_registros_competencia(
                supabase,
                "Questor",
                competencia,
            )
        )

    except Exception as erro:

        st.error(
            "Não foi possível consultar o banco de dados."
        )

        st.exception(erro)

        return

    # ========================================================
    # COMPETÊNCIA NOVA
    # ========================================================

    if registros_existentes == 0:

        st.success(
            f"A competência {mes_nome}/{ano} "
            "ainda não foi importada."
        )

        st.write(
            f"Serão gravados **{quantidade_clientes} clientes**."
        )

        registros = preparar_registros_banco(
            df,
            competencia,
            arquivo.name,
        )

        if st.button(
            f"Importar {mes_nome}/{ano}",
            type="primary",
            use_container_width=True,
        ):

            try:

                with st.spinner(
                    "Importando dados para o banco..."
                ):

                    total_inseridos = (
                        inserir_registros_em_lotes(
                            supabase,
                            registros,
                        )
                    )

                st.success(
                    f"Importação concluída. "
                    f"{total_inseridos} registros "
                    f"foram gravados para "
                    f"{mes_nome}/{ano}."
                )

                st.balloons()

                st.rerun()

            except Exception as erro:

                st.error(
                    "A importação não foi concluída."
                )

                st.exception(erro)

    # ========================================================
    # COMPETÊNCIA JÁ EXISTENTE
    # ========================================================

    else:

        st.warning(
            f"A competência **{mes_nome}/{ano}** "
            f"já possui **{registros_existentes} registros** "
            "do Questor no banco de dados."
        )

        st.info(
            "Para evitar duplicidades, uma nova importação "
            "não será realizada automaticamente. "
            "Se este arquivo deve substituir o arquivo anterior, "
            "utilize a opção abaixo."
        )

        confirmar = st.checkbox(
            f"Confirmo que desejo substituir completamente "
            f"os dados de {mes_nome}/{ano}.",
            key=(
                f"confirmar_substituicao_"
                f"{ano}_{mes_numero}"
            ),
        )

        registros = preparar_registros_banco(
            df,
            competencia,
            arquivo.name,
        )

        if confirmar:

            if st.button(
                f"Substituir {mes_nome}/{ano}",
                type="primary",
                use_container_width=True,
            ):

                try:

                    with st.spinner(
                        "Substituindo a competência..."
                    ):

                        # Apaga SOMENTE:
                        # Questor + competência selecionada
                        excluir_competencia(
                            supabase,
                            "Questor",
                            competencia,
                        )

                        total_inseridos = (
                            inserir_registros_em_lotes(
                                supabase,
                                registros,
                            )
                        )

                    st.success(
                        f"{mes_nome}/{ano} foi substituído "
                        f"com sucesso. "
                        f"{total_inseridos} registros "
                        "foram gravados."
                    )

                    st.rerun()

                except Exception as erro:

                    st.error(
                        "Não foi possível concluir "
                        "a substituição."
                    )

                    st.exception(erro)
