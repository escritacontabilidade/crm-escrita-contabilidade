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
# ANÁLISE DE CRESCIMENTO POR CLIENTE
# ============================================================

def buscar_dados_analise_clientes(supabase, sistema="Questor"):
    """Busca todo o histórico necessário para comparação cliente a cliente."""
    campos = (
        "competencia,codigo_cliente,cliente,"
        "folha_pagamento,processos,notas_fiscais,contabil,faturamento"
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
            .order("competencia")
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

    df = pd.DataFrame(todos_registros)
    df["competencia"] = pd.to_datetime(df["competencia"], errors="coerce")
    df = df.dropna(subset=["competencia"])

    for coluna in ["folha_pagamento", "processos", "notas_fiscais", "contabil", "faturamento"]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").fillna(0)

    df["codigo_cliente"] = df["codigo_cliente"].astype(str)
    return df


def calcular_variacao_percentual(atual, referencia):
    """Calcula variação percentual, evitando divisão por zero."""
    if pd.isna(referencia) or float(referencia) == 0:
        return None
    return ((float(atual) - float(referencia)) / abs(float(referencia))) * 100


def formatar_percentual(valor):
    if valor is None or pd.isna(valor):
        return "—"
    sinal = "+" if float(valor) > 0 else ""
    return f"{sinal}{float(valor):.1f}%".replace(".", ",")


def exibir_analise_crescimento_clientes(supabase):
    st.subheader("Análise de Crescimento por Cliente")

    st.caption(
        "Compare cada cliente com seu próprio histórico. "
        "Nesta etapa a análise é diagnóstica: ainda não gera reajustes automáticos."
    )

    try:
        df = buscar_dados_analise_clientes(supabase, "Questor")
    except Exception as erro:
        st.error("Não foi possível carregar os dados para análise por cliente.")
        st.exception(erro)
        return

    if df.empty:
        st.info("Ainda não existem dados suficientes para realizar a análise.")
        return

    competencias = sorted(df["competencia"].dropna().unique(), reverse=True)

    if len(competencias) < 2:
        st.info(
            "É necessário ter pelo menos duas competências importadas "
            "para comparar a evolução dos clientes."
        )
        return

    nomes_meses = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
    }

    opcoes = {
        f"{nomes_meses[pd.Timestamp(data).month]}/{pd.Timestamp(data).year}":
        pd.Timestamp(data)
        for data in competencias
    }

    competencia_label = st.selectbox(
        "Competência para análise",
        options=list(opcoes.keys()),
        index=0,
        key="analise_crescimento_competencia",
    )
    competencia_atual = opcoes[competencia_label]

    historico_anterior = df[df["competencia"] < competencia_atual].copy()
    atual = df[df["competencia"] == competencia_atual].copy()

    if historico_anterior.empty:
        st.info(
            f"{competencia_label} é a primeira competência disponível. "
            "Selecione um mês posterior para realizar comparações."
        )
        return

    # Diagnóstico global da competência antes de analisar clientes.
    total_clientes_atual = atual["codigo_cliente"].nunique()
    clientes_por_mes = (
        historico_anterior.groupby("competencia")["codigo_cliente"].nunique()
    )
    mediana_clientes = float(clientes_por_mes.median()) if not clientes_por_mes.empty else 0

    totais_atual = atual[["folha_pagamento", "processos", "notas_fiscais", "contabil", "faturamento"]].sum()
    totais_hist = (
        historico_anterior
        .groupby("competencia")[["folha_pagamento", "processos", "notas_fiscais", "contabil", "faturamento"]]
        .sum()
    )
    medianas_hist = totais_hist.median() if not totais_hist.empty else pd.Series(dtype=float)

    alertas_competencia = []

    if mediana_clientes > 0 and total_clientes_atual < mediana_clientes * 0.85:
        alertas_competencia.append(
            f"quantidade de clientes {((total_clientes_atual / mediana_clientes) - 1) * 100:.1f}% "
            "abaixo da mediana dos meses anteriores"
        )

    for coluna, rotulo in [
        ("folha_pagamento", "Folha"),
        ("processos", "Processos"),
        ("notas_fiscais", "Notas Fiscais"),
        ("contabil", "Contábil"),
        ("faturamento", "Faturamento"),
    ]:
        referencia = float(medianas_hist.get(coluna, 0) or 0)
        atual_total = float(totais_atual.get(coluna, 0) or 0)
        if referencia > 0 and atual_total < referencia * 0.50:
            alertas_competencia.append(
                f"{rotulo} total mais de 50% abaixo da mediana histórica"
            )

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Clientes no mês", formatar_numero(total_clientes_atual))
    col_b.metric(
        "Meses anteriores usados",
        formatar_numero(historico_anterior["competencia"].nunique()),
    )
    col_c.metric(
        "Confiabilidade da competência",
        "Atenção" if alertas_competencia else "Normal",
    )

    if alertas_competencia:
        st.warning(
            "A competência selecionada apresenta sinais de possível anormalidade: "
            + "; ".join(alertas_competencia)
            + ". Analise os resultados com cautela antes de qualquer decisão comercial."
        )
    else:
        st.success(
            "A competência não apresentou indícios globais fortes de arquivo incompleto "
            "nos critérios preliminares de validação."
        )

    # Estatísticas históricas por cliente.
    hist_ordenado = historico_anterior.sort_values("competencia")

    medias = (
        hist_ordenado
        .groupby("codigo_cliente", as_index=False)
        .agg(
            media_folha=("folha_pagamento", "mean"),
            media_processos=("processos", "mean"),
            media_notas_fiscais=("notas_fiscais", "mean"),
            media_contabil=("contabil", "mean"),
            media_faturamento=("faturamento", "mean"),
            meses_historico=("competencia", "nunique"),
        )
    )

    primeiros = (
        hist_ordenado
        .groupby("codigo_cliente", as_index=False)
        .first()[
            [
                "codigo_cliente",
                "competencia",
                "folha_pagamento",
                "processos",
                "notas_fiscais",
                "contabil",
                "faturamento",
            ]
        ]
        .rename(
            columns={
                "competencia": "primeira_competencia",
                "folha_pagamento": "primeira_folha",
                "processos": "primeiros_processos",
                "notas_fiscais": "primeiras_notas_fiscais",
                "contabil": "primeiro_contabil",
                "faturamento": "primeiro_faturamento",
            }
        )
    )

    analise = (
        atual[
            [
                "codigo_cliente",
                "cliente",
                "folha_pagamento",
                "processos",
                "notas_fiscais",
                "contabil",
                "faturamento",
            ]
        ]
        .merge(medias, on="codigo_cliente", how="left")
        .merge(primeiros, on="codigo_cliente", how="left")
    )

    for metrica in ["folha", "processos", "notas_fiscais", "contabil", "faturamento"]:
        atual_col = {
            "folha": "folha_pagamento",
            "processos": "processos",
            "notas_fiscais": "notas_fiscais",
            "contabil": "contabil",
            "faturamento": "faturamento",
        }[metrica]
        media_col = {
            "folha": "media_folha",
            "processos": "media_processos",
            "notas_fiscais": "media_notas_fiscais",
            "contabil": "media_contabil",
            "faturamento": "media_faturamento",
        }[metrica]
        primeiro_col = {
            "folha": "primeira_folha",
            "processos": "primeiros_processos",
            "notas_fiscais": "primeiras_notas_fiscais",
            "contabil": "primeiro_contabil",
            "faturamento": "primeiro_faturamento",
        }[metrica]

        analise[f"var_{metrica}_media"] = analise.apply(
            lambda linha: calcular_variacao_percentual(
                linha[atual_col], linha[media_col]
            ),
            axis=1,
        )
        analise[f"var_{metrica}_inicio"] = analise.apply(
            lambda linha: calcular_variacao_percentual(
                linha[atual_col], linha[primeiro_col]
            ),
            axis=1,
        )

    st.markdown("#### Comparativo individual")

    metrica_escolhida = st.radio(
        "Indicador principal",
        options=["Folha", "Processos", "Notas Fiscais", "Contábil", "Faturamento"],
        horizontal=True,
        key="analise_crescimento_metrica",
    )

    mapa = {
        "Folha": (
            "folha_pagamento", "media_folha", "primeira_folha",
            "var_folha_media", "var_folha_inicio"
        ),
        "Processos": (
            "processos", "media_processos", "primeiros_processos",
            "var_processos_media", "var_processos_inicio"
        ),
        "Notas Fiscais": (
            "notas_fiscais", "media_notas_fiscais", "primeiras_notas_fiscais",
            "var_notas_fiscais_media", "var_notas_fiscais_inicio"
        ),
        "Contábil": (
            "contabil", "media_contabil", "primeiro_contabil",
            "var_contabil_media", "var_contabil_inicio"
        ),
        "Faturamento": (
            "faturamento", "media_faturamento", "primeiro_faturamento",
            "var_faturamento_media", "var_faturamento_inicio"
        ),
    }

    atual_col, media_col, primeiro_col, var_media_col, var_inicio_col = mapa[metrica_escolhida]

    visual = analise[
        [
            "codigo_cliente", "cliente", "meses_historico",
            atual_col, media_col, primeiro_col,
            var_media_col, var_inicio_col,
        ]
    ].copy()

    visual = visual.sort_values(
        var_media_col,
        ascending=False,
        na_position="last",
    )

    if metrica_escolhida == "Faturamento":
        for coluna in [atual_col, media_col, primeiro_col]:
            visual[coluna] = visual[coluna].apply(formatar_moeda)
    else:
        for coluna in [atual_col, media_col, primeiro_col]:
            visual[coluna] = visual[coluna].apply(formatar_numero)

    visual[var_media_col] = visual[var_media_col].apply(formatar_percentual)
    visual[var_inicio_col] = visual[var_inicio_col].apply(formatar_percentual)
    visual["meses_historico"] = visual["meses_historico"].fillna(0).apply(formatar_numero)

    visual = visual.rename(
        columns={
            "codigo_cliente": "Código",
            "cliente": "Cliente",
            "meses_historico": "Meses anteriores",
            atual_col: competencia_label,
            media_col: "Média anterior",
            primeiro_col: "Primeiro mês",
            var_media_col: "Variação x média",
            var_inicio_col: "Variação x início",
        }
    )

    st.dataframe(
        visual,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "A média considera somente competências anteriores à selecionada. "
        "Quando a referência histórica é zero, a variação percentual é exibida como “—” "
        "para evitar conclusões matematicamente enganosas."
    )




# ============================================================
# RADAR DE REVISÃO DE HONORÁRIOS
# ============================================================

def _valor_seguro(valor):
    try:
        if pd.isna(valor):
            return 0.0
        return float(valor)
    except Exception:
        return 0.0


def _crescimento_material(atual, referencia, percentual_minimo, aumento_minimo):
    """
    Evita alertas causados apenas por bases históricas muito pequenas.
    Retorna (atingiu_criterio, variacao_percentual).
    """
    atual = _valor_seguro(atual)
    referencia = _valor_seguro(referencia)

    if referencia <= 0:
        return False, None

    variacao_abs = atual - referencia
    variacao_pct = ((atual - referencia) / abs(referencia)) * 100

    atingiu = (
        variacao_pct >= percentual_minimo
        and variacao_abs >= aumento_minimo
    )

    return atingiu, variacao_pct


def calcular_radar_reajuste(analise):
    """
    Classifica clientes conforme crescimento de carga operacional.

    IMPORTANTE:
    O radar NÃO calcula reajuste de preço e NÃO afirma que o honorário
    está incorreto. Ele identifica clientes que merecem revisão comercial.

    Regras:
    - mínimo de 3 meses anteriores para classificação conclusiva;
    - compara mês atual com a média dos meses anteriores;
    - usa também o primeiro mês como evidência de crescimento sustentado;
    - exige crescimento percentual + crescimento absoluto mínimo;
    - Folha, Processos, Notas Fiscais, Contábil e Faturamento são tratados como indicadores de crescimento.
    """
    if analise.empty:
        return analise.copy()

    radar = analise.copy()

    resultados = []

    for _, linha in radar.iterrows():
        meses = int(_valor_seguro(linha.get("meses_historico", 0)))

        atual_folha = _valor_seguro(linha.get("folha_pagamento"))
        media_folha = _valor_seguro(linha.get("media_folha"))
        primeira_folha = _valor_seguro(linha.get("primeira_folha"))

        atual_processos = _valor_seguro(linha.get("processos"))
        media_processos = _valor_seguro(linha.get("media_processos"))
        primeiros_processos = _valor_seguro(linha.get("primeiros_processos"))

        atual_notas = _valor_seguro(linha.get("notas_fiscais"))
        media_notas = _valor_seguro(linha.get("media_notas_fiscais"))
        primeiras_notas = _valor_seguro(linha.get("primeiras_notas_fiscais"))

        atual_contabil = _valor_seguro(linha.get("contabil"))
        media_contabil = _valor_seguro(linha.get("media_contabil"))
        primeiro_contabil = _valor_seguro(linha.get("primeiro_contabil"))

        atual_faturamento = _valor_seguro(linha.get("faturamento"))
        media_faturamento = _valor_seguro(linha.get("media_faturamento"))
        primeiro_faturamento = _valor_seguro(linha.get("primeiro_faturamento"))

        if meses < 3:
            resultados.append({
                "classificacao": "Sem histórico suficiente",
                "pontuacao": 0,
                "motivos": f"Apenas {meses} mês(es) anterior(es) disponível(is).",
                "indicadores_alerta": 0,
            })
            continue

        pontos = 0
        motivos = []
        indicadores_alerta = 0

        # ----------------------------------------------------
        # FOLHA
        # Materialidade: pelo menos +5 eventos e +20%.
        # Crescimento forte: +50% e pelo menos +10 eventos.
        # ----------------------------------------------------
        folha_atencao, var_folha = _crescimento_material(
            atual_folha, media_folha, 20, 5
        )
        folha_forte, _ = _crescimento_material(
            atual_folha, media_folha, 50, 10
        )

        if folha_forte:
            pontos += 2
            indicadores_alerta += 1
            motivos.append(
                f"Folha {formatar_percentual(var_folha)} acima da média histórica"
            )
        elif folha_atencao:
            pontos += 1
            indicadores_alerta += 1
            motivos.append(
                f"Folha {formatar_percentual(var_folha)} acima da média histórica"
            )

        # ----------------------------------------------------
        # PROCESSOS
        # Materialidade: pelo menos +10 processos e +20%.
        # Crescimento forte: +50% e pelo menos +25 processos.
        # ----------------------------------------------------
        proc_atencao, var_proc = _crescimento_material(
            atual_processos, media_processos, 20, 10
        )
        proc_forte, _ = _crescimento_material(
            atual_processos, media_processos, 50, 25
        )

        if proc_forte:
            pontos += 2
            indicadores_alerta += 1
            motivos.append(
                f"Processos {formatar_percentual(var_proc)} acima da média histórica"
            )
        elif proc_atencao:
            pontos += 1
            indicadores_alerta += 1
            motivos.append(
                f"Processos {formatar_percentual(var_proc)} acima da média histórica"
            )

        # ----------------------------------------------------
        # NOTAS FISCAIS (Entradas + Saídas)
        # Materialidade: +20% e pelo menos +20 notas.
        # Forte: +50% e pelo menos +50 notas.
        # ----------------------------------------------------
        notas_atencao, var_notas = _crescimento_material(
            atual_notas, media_notas, 20, 20
        )
        notas_forte, _ = _crescimento_material(
            atual_notas, media_notas, 50, 50
        )

        if notas_forte:
            pontos += 2
            indicadores_alerta += 1
            motivos.append(
                f"Notas Fiscais {formatar_percentual(var_notas)} acima da média histórica"
            )
        elif notas_atencao:
            pontos += 1
            indicadores_alerta += 1
            motivos.append(
                f"Notas Fiscais {formatar_percentual(var_notas)} acima da média histórica"
            )

        # ----------------------------------------------------
        # CONTÁBIL
        # Materialidade: +20% e pelo menos +50 lançamentos.
        # Forte: +50% e pelo menos +100 lançamentos.
        # ----------------------------------------------------
        contabil_atencao, var_contabil = _crescimento_material(
            atual_contabil, media_contabil, 20, 50
        )
        contabil_forte, _ = _crescimento_material(
            atual_contabil, media_contabil, 50, 100
        )

        if contabil_forte:
            pontos += 2
            indicadores_alerta += 1
            motivos.append(
                f"Contábil {formatar_percentual(var_contabil)} acima da média histórica"
            )
        elif contabil_atencao:
            pontos += 1
            indicadores_alerta += 1
            motivos.append(
                f"Contábil {formatar_percentual(var_contabil)} acima da média histórica"
            )

        # ----------------------------------------------------
        # FATURAMENTO DO CLIENTE
        # É proxy de porte/complexidade, não honorário da Escrita.
        # Materialidade: +20% e pelo menos R$ 50 mil.
        # Forte: +50% e pelo menos R$ 100 mil.
        # ----------------------------------------------------
        fat_atencao, var_fat = _crescimento_material(
            atual_faturamento, media_faturamento, 20, 50000
        )
        fat_forte, _ = _crescimento_material(
            atual_faturamento, media_faturamento, 50, 100000
        )

        if fat_forte:
            pontos += 2
            indicadores_alerta += 1
            motivos.append(
                f"Faturamento {formatar_percentual(var_fat)} acima da média histórica"
            )
        elif fat_atencao:
            pontos += 1
            indicadores_alerta += 1
            motivos.append(
                f"Faturamento {formatar_percentual(var_fat)} acima da média histórica"
            )

        # ----------------------------------------------------
        # CRESCIMENTO SUSTENTADO DESDE O PRIMEIRO MÊS
        # Só adiciona 1 ponto total, evitando dupla contagem excessiva.
        # ----------------------------------------------------
        sustentados = []

        folha_inicio, var_folha_inicio = _crescimento_material(
            atual_folha, primeira_folha, 30, 5
        )
        if folha_inicio:
            sustentados.append(f"Folha {formatar_percentual(var_folha_inicio)}")

        proc_inicio, var_proc_inicio = _crescimento_material(
            atual_processos, primeiros_processos, 30, 10
        )
        if proc_inicio:
            sustentados.append(f"Processos {formatar_percentual(var_proc_inicio)}")

        notas_inicio, var_notas_inicio = _crescimento_material(
            atual_notas, primeiras_notas, 30, 20
        )
        if notas_inicio:
            sustentados.append(f"Notas Fiscais {formatar_percentual(var_notas_inicio)}")

        contabil_inicio, var_contabil_inicio = _crescimento_material(
            atual_contabil, primeiro_contabil, 30, 50
        )
        if contabil_inicio:
            sustentados.append(f"Contábil {formatar_percentual(var_contabil_inicio)}")

        fat_inicio, var_fat_inicio = _crescimento_material(
            atual_faturamento, primeiro_faturamento, 30, 50000
        )
        if fat_inicio:
            sustentados.append(f"Faturamento {formatar_percentual(var_fat_inicio)}")

        if sustentados:
            pontos += 1
            motivos.append(
                "Crescimento desde o início: " + ", ".join(sustentados)
            )

        # ----------------------------------------------------
        # CLASSIFICAÇÃO
        # ----------------------------------------------------
        if pontos >= 5 or indicadores_alerta >= 3:
            classificacao = "Prioridade"
        elif pontos >= 3 or indicadores_alerta >= 2:
            classificacao = "Revisar honorários"
        elif pontos >= 1:
            classificacao = "Atenção"
        else:
            classificacao = "Normal"
            motivos.append("Sem crescimento material nos critérios do radar.")

        resultados.append({
            "classificacao": classificacao,
            "pontuacao": pontos,
            "motivos": "; ".join(motivos),
            "indicadores_alerta": indicadores_alerta,
        })

    resultado_df = pd.DataFrame(resultados, index=radar.index)

    for coluna in resultado_df.columns:
        radar[coluna] = resultado_df[coluna]

    return radar


def exibir_radar_reajuste(supabase):
    st.subheader("Radar de Revisão de Honorários")

    st.caption(
        "Prioriza clientes cuja movimentação cresceu em relação ao próprio histórico. "
        "O radar é um instrumento de triagem comercial: ele não calcula automaticamente "
        "o novo honorário."
    )

    try:
        df = buscar_dados_analise_clientes(supabase, "Questor")
    except Exception as erro:
        st.error("Não foi possível carregar os dados do Radar de Revisão.")
        st.exception(erro)
        return

    if df.empty:
        st.info("Ainda não existem dados suficientes para o radar.")
        return

    competencias = sorted(df["competencia"].dropna().unique(), reverse=True)

    if len(competencias) < 2:
        st.info("É necessário ter pelo menos duas competências importadas.")
        return

    nomes_meses = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
    }

    opcoes = {
        f"{nomes_meses[pd.Timestamp(data).month]}/{pd.Timestamp(data).year}":
        pd.Timestamp(data)
        for data in competencias
    }

    competencia_label = st.selectbox(
        "Competência do radar",
        options=list(opcoes.keys()),
        index=0,
        key="radar_reajuste_competencia",
    )
    competencia_atual = opcoes[competencia_label]

    historico_anterior = df[df["competencia"] < competencia_atual].copy()
    atual = df[df["competencia"] == competencia_atual].copy()

    if historico_anterior.empty:
        st.info(
            f"{competencia_label} é a primeira competência disponível. "
            "Selecione um mês posterior."
        )
        return

    hist_ordenado = historico_anterior.sort_values("competencia")

    medias = (
        hist_ordenado
        .groupby("codigo_cliente", as_index=False)
        .agg(
            media_folha=("folha_pagamento", "mean"),
            media_processos=("processos", "mean"),
            media_notas_fiscais=("notas_fiscais", "mean"),
            media_contabil=("contabil", "mean"),
            media_faturamento=("faturamento", "mean"),
            meses_historico=("competencia", "nunique"),
        )
    )

    primeiros = (
        hist_ordenado
        .groupby("codigo_cliente", as_index=False)
        .first()[
            [
                "codigo_cliente",
                "folha_pagamento",
                "processos",
                "notas_fiscais",
                "contabil",
                "faturamento",
            ]
        ]
        .rename(
            columns={
                "folha_pagamento": "primeira_folha",
                "processos": "primeiros_processos",
                "notas_fiscais": "primeiras_notas_fiscais",
                "contabil": "primeiro_contabil",
                "faturamento": "primeiro_faturamento",
            }
        )
    )

    analise = (
        atual[
            [
                "codigo_cliente",
                "cliente",
                "folha_pagamento",
                "processos",
                "notas_fiscais",
                "contabil",
                "faturamento",
            ]
        ]
        .merge(medias, on="codigo_cliente", how="left")
        .merge(primeiros, on="codigo_cliente", how="left")
    )

    radar = calcular_radar_reajuste(analise)

    ordem = {
        "Prioridade": 1,
        "Revisar honorários": 2,
        "Atenção": 3,
        "Normal": 4,
        "Sem histórico suficiente": 5,
    }

    radar["ordem"] = radar["classificacao"].map(ordem).fillna(99)
    radar = radar.sort_values(
        ["ordem", "pontuacao", "cliente"],
        ascending=[True, False, True],
    )

    cont_prioridade = int((radar["classificacao"] == "Prioridade").sum())
    cont_revisar = int((radar["classificacao"] == "Revisar honorários").sum())
    cont_atencao = int((radar["classificacao"] == "Atenção").sum())
    cont_normal = int((radar["classificacao"] == "Normal").sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Prioridade", formatar_numero(cont_prioridade))
    col2.metric("Revisar honorários", formatar_numero(cont_revisar))
    col3.metric("Atenção", formatar_numero(cont_atencao))
    col4.metric("Normal", formatar_numero(cont_normal))

    st.markdown("#### Filtros do radar")

    col_filtro1, col_filtro2 = st.columns([1, 2])

    with col_filtro1:
        classificacoes_disponiveis = [
            "Prioridade",
            "Revisar honorários",
            "Atenção",
            "Normal",
            "Sem histórico suficiente",
        ]

        classificacoes = st.multiselect(
            "Classificação",
            options=classificacoes_disponiveis,
            default=[
                "Prioridade",
                "Revisar honorários",
                "Atenção",
            ],
            key="radar_filtro_classificacao",
        )

    with col_filtro2:
        busca_cliente = st.text_input(
            "Buscar cliente",
            placeholder="Digite parte do nome ou o código Questor",
            key="radar_busca_cliente",
        )

    filtrado = radar.copy()

    if classificacoes:
        filtrado = filtrado[
            filtrado["classificacao"].isin(classificacoes)
        ]
    else:
        filtrado = filtrado.iloc[0:0]

    if busca_cliente.strip():
        termo = busca_cliente.strip().lower()
        filtrado = filtrado[
            filtrado["cliente"].astype(str).str.lower().str.contains(
                termo, regex=False
            )
            |
            filtrado["codigo_cliente"].astype(str).str.lower().str.contains(
                termo, regex=False
            )
        ]

    st.markdown("#### Clientes sinalizados")

    if filtrado.empty:
        st.info("Nenhum cliente encontrado com os filtros selecionados.")
        return

    visual = filtrado[
        [
            "classificacao",
            "codigo_cliente",
            "cliente",
            "meses_historico",
            "folha_pagamento",
            "processos",
            "notas_fiscais",
            "contabil",
            "faturamento",
            "pontuacao",
            "motivos",
        ]
    ].copy()

    visual["meses_historico"] = (
        visual["meses_historico"].fillna(0).apply(formatar_numero)
    )
    visual["folha_pagamento"] = visual["folha_pagamento"].apply(formatar_numero)
    visual["processos"] = visual["processos"].apply(formatar_numero)
    visual["notas_fiscais"] = visual["notas_fiscais"].apply(formatar_numero)
    visual["contabil"] = visual["contabil"].apply(formatar_numero)
    visual["faturamento"] = visual["faturamento"].apply(formatar_moeda)

    visual = visual.rename(
        columns={
            "classificacao": "Classificação",
            "codigo_cliente": "Código",
            "cliente": "Cliente",
            "meses_historico": "Meses anteriores",
            "folha_pagamento": "Folha atual",
            "processos": "Processos atuais",
            "notas_fiscais": "Notas Fiscais atuais",
            "contabil": "Contábil atual",
            "faturamento": "Faturamento atual",
            "pontuacao": "Pontos",
            "motivos": "Motivo do alerta",
        }
    )

    st.dataframe(
        visual,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Motivo do alerta": st.column_config.TextColumn(
                "Motivo do alerta",
                width="large",
            ),
        },
    )

    st.caption(
        f"{len(filtrado)} cliente(s) exibido(s). "
        "Use o radar como fila de revisão. A decisão de reajuste deve considerar "
        "também honorário atual, escopo contratado, regime tributário, particularidades "
        "operacionais e rentabilidade do cliente."
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

    # ========================================================
    # ANÁLISE DE CRESCIMENTO POR CLIENTE
    # ========================================================

    exibir_analise_crescimento_clientes(supabase)

    st.divider()

    # ========================================================
    # RADAR DE REVISÃO DE HONORÁRIOS
    # ========================================================

    exibir_radar_reajuste(supabase)

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
