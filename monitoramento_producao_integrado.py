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


COLUNAS_QUESTOR = {
    "Folha Pgto. Questor": "folha_pagamento",
    "Admissão  Questor": "admissoes",
    "Rescisão  Questor": "rescisoes",
    "Contábil  Questor": "contabil",
    "Entradas  Questor": "entradas",
    "Saídas  Questor": "saidas",
    "Processos  Questor": "processos",
    "Faturamento  Questor": "faturamento",
}

COLUNAS_CONTABIT = {
    "Folha Pgto. Contabit": "folha_pagamento",
    "Admissão Contabit": "admissoes",
    "Rescisão Contabit": "rescisoes",
    "Contábil Contabit": "contabil",
    "Entradas Contabit": "entradas",
    "Saídas Contabit": "saidas",
    "Faturamento Contabit": "faturamento",
}


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

def preparar_arquivo_producao(arquivo):
    """
    Lê o arquivo mensal e separa fisicamente os blocos Questor e Contabit.
    Retorna dois DataFrames independentes.
    """
    try:
        df = pd.read_excel(arquivo, sheet_name="Export")
    except ValueError:
        raise ValueError("Não foi encontrada a aba 'Export' no arquivo.")
    except Exception as erro:
        raise ValueError(f"Não foi possível ler o arquivo Excel: {erro}")

    df.columns = [str(coluna).strip() for coluna in df.columns]

    # Como o Excel pode trazer espaços duplos nos títulos, fazemos a
    # correspondência ignorando diferenças de espaços.
    def chave_coluna(nome):
        return " ".join(str(nome).strip().split()).lower()

    mapa_real = {chave_coluna(c): c for c in df.columns}

    def localizar(nome_esperado):
        return mapa_real.get(chave_coluna(nome_esperado))

    cliente_real = localizar("Cliente")
    if not cliente_real:
        raise ValueError("A coluna 'Cliente' não foi encontrada.")

    faltantes = []
    for nome in list(COLUNAS_QUESTOR.keys()) + list(COLUNAS_CONTABIT.keys()):
        if localizar(nome) is None:
            faltantes.append(nome)

    if faltantes:
        raise ValueError(
            "O arquivo não possui todas as colunas esperadas do novo layout. "
            "Colunas ausentes: " + ", ".join(faltantes)
        )

    base = df.copy()
    base = base.dropna(how="all")
    base["Cliente"] = base[cliente_real].astype(str).str.strip()
    base = base[
        ~base["Cliente"].str.lower().isin(["", "nan", "none"])
    ].copy()
    base = base[
        ~base["Cliente"].str.lower().str.startswith("total")
    ].copy()

    clientes_separados = base["Cliente"].apply(separar_codigo_cliente)
    base["codigo_questor"] = clientes_separados.apply(lambda x: x[0])
    base["razao_social"] = clientes_separados.apply(lambda x: x[1])

    base = base[base["codigo_questor"].notna()].copy()
    base["codigo_questor"] = base["codigo_questor"].astype(str).str.strip()
    base = base[
        base["codigo_questor"].str.match(r"^\d+$", na=False)
    ].copy()

    def montar_bloco(mapeamento, sistema):
        saida = base[["codigo_questor", "razao_social"]].copy()

        for coluna_excel, coluna_interna in mapeamento.items():
            coluna_real = localizar(coluna_excel)
            saida[coluna_interna] = base[coluna_real].apply(converter_numero)

        # Contabit não possui Processos no arquivo.
        if "processos" not in saida.columns:
            saida["processos"] = 0.0

        saida["notas_fiscais"] = saida["entradas"] + saida["saidas"]
        saida["sistema"] = sistema

        colunas_movimento = [
            "folha_pagamento", "admissoes", "rescisoes", "contabil",
            "entradas", "saidas", "notas_fiscais", "processos", "faturamento"
        ]

        # Não cria registro de uma origem que esteja totalmente zerada
        # para aquele cliente.
        saida = saida[
            saida[colunas_movimento].abs().sum(axis=1) > 0
        ].copy()

        saida = saida.drop_duplicates(
            subset=["codigo_questor"], keep="last"
        )

        return saida.reset_index(drop=True)

    return (
        montar_bloco(COLUNAS_QUESTOR, "Questor"),
        montar_bloco(COLUNAS_CONTABIT, "Contabit"),
    )


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
    sistema,
):
    """
    Converte o DataFrame validado em registros
    compatíveis com producao_clientes.
    """

    registros = []

    for _, linha in df.iterrows():

        registro = {
            "sistema": sistema,
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


def buscar_historico_consolidado(supabase):
    campos = (
        "sistema,competencia,codigo_cliente,folha_pagamento,"
        "admissao,rescisao,contabil,entradas,saidas,"
        "notas_fiscais,processos,faturamento"
    )
    todos = []
    inicio = 0
    tamanho = 1000

    while True:
        resultado = (
            supabase.table("producao_clientes")
            .select(campos)
            .in_("sistema", ["Questor", "Contabit"])
            .order("competencia", desc=True)
            .range(inicio, inicio + tamanho - 1)
            .execute()
        )
        lote = resultado.data or []
        todos.extend(lote)
        if len(lote) < tamanho:
            break
        inicio += tamanho

    if not todos:
        return pd.DataFrame()

    df = pd.DataFrame(todos)
    df["competencia"] = pd.to_datetime(df["competencia"], errors="coerce")
    df = df.dropna(subset=["competencia"])

    numericas = [
        "folha_pagamento", "admissao", "rescisao", "contabil",
        "entradas", "saidas", "notas_fiscais", "processos", "faturamento"
    ]
    for coluna in numericas:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").fillna(0)

    return (
        df.groupby("competencia", as_index=False)
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


def exibir_historico_importacoes(supabase):
    st.subheader("Histórico de Importações")

    origem = st.radio(
        "Visão do histórico",
        options=["Consolidado", "Questor", "Contabit"],
        horizontal=True,
        key="historico_origem",
    )

    try:
        if origem == "Consolidado":
            historico = buscar_historico_consolidado(supabase)
        else:
            historico = buscar_historico_importacoes(supabase, origem)
    except Exception as erro:
        st.error("Não foi possível carregar o histórico de importações.")
        st.exception(erro)
        return

    if historico.empty:
        st.info(f"Ainda não existem competências para a visão {origem}.")
        return

    nomes_meses = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
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

    visual = visual[[
        "Competência", "Clientes", "Folha", "Admissões", "Rescisões",
        "Contábil", "Entradas", "Saídas", "Notas Fiscais",
        "Processos", "Faturamento"
    ]]

    st.dataframe(visual, use_container_width=True, hide_index=True)
    st.caption(f"{len(visual)} competência(s) exibida(s) — visão {origem}.")


# ============================================================
# ANÁLISE DE CRESCIMENTO POR CLIENTE
# ============================================================

def buscar_dados_analise_clientes(supabase, sistema="Consolidado"):
    """Busca histórico por origem ou consolida Questor + Contabit por cliente/mês."""
    campos = (
        "sistema,competencia,codigo_cliente,cliente,"
        "folha_pagamento,processos,notas_fiscais,contabil,faturamento"
    )

    todos_registros = []
    inicio = 0
    tamanho_pagina = 1000

    while True:
        consulta = (
            supabase
            .table("producao_clientes")
            .select(campos)
        )

        if sistema in ["Questor", "Contabit"]:
            consulta = consulta.eq("sistema", sistema)
        else:
            consulta = consulta.in_("sistema", ["Questor", "Contabit"])

        resultado = (
            consulta
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

    numericas = [
        "folha_pagamento", "processos", "notas_fiscais",
        "contabil", "faturamento"
    ]
    for coluna in numericas:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").fillna(0)

    df["codigo_cliente"] = df["codigo_cliente"].astype(str)

    if sistema == "Consolidado":
        # Soma as duas origens sem gravar uma terceira linha no banco.
        df = (
            df.groupby(
                ["competencia", "codigo_cliente"],
                as_index=False
            )
            .agg(
                cliente=("cliente", "first"),
                folha_pagamento=("folha_pagamento", "sum"),
                processos=("processos", "sum"),
                notas_fiscais=("notas_fiscais", "sum"),
                contabil=("contabil", "sum"),
                faturamento=("faturamento", "sum"),
            )
        )

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

    origem_analise = st.radio(
        "Origem dos dados",
        options=["Consolidado", "Questor", "Contabit"],
        horizontal=True,
        key="analise_origem_dados",
    )

    try:
        df = buscar_dados_analise_clientes(supabase, origem_analise)
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

    origem_radar = st.radio(
        "Origem dos dados do radar",
        options=["Consolidado", "Questor", "Contabit"],
        horizontal=True,
        key="radar_origem_dados",
    )

    try:
        df = buscar_dados_analise_clientes(supabase, origem_radar)
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
    admin = (
        st.session_state.get("autenticado") is True
        and st.session_state.get("perfil_usuario") == "admin"
    )
    if admin:
        abas = st.tabs(["Produção e Radar", "Honorários", "Produção × Honorários"])
    else:
        abas = st.tabs(["Produção e Radar"])

    if admin:
        # Os dados financeiros nunca são consultados pelo cliente Supabase comum.
        # O módulo administrativo revalida o perfil antes de cada consulta.
        from monitoramento_honorarios import tela_honorarios, tela_cruzamento
        with abas[1]:
            tela_honorarios()
        with abas[2]:
            tela_cruzamento()

    with abas[0]:
        st.write("Importação, histórico e acompanhamento de Questor e Contabit.")
        exibir_historico_importacoes(supabase)
        st.divider()
        exibir_analise_crescimento_clientes(supabase)
        st.divider()
        exibir_radar_reajuste(supabase)
        st.divider()
        st.subheader("Importar produção — Questor + Contabit")

        st.info(
            "O novo arquivo mensal contém dois blocos de produção. "
            "O sistema separará Questor e Contabit automaticamente e gravará "
            "cada origem de forma independente."
        )

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
            anos = list(range(ano_atual - 5, ano_atual + 2))
            ano = st.selectbox(
                "Ano da competência *",
                options=anos,
                index=anos.index(ano_atual),
                key="producao_ano_competencia",
            )

        mes_numero = MESES[mes_nome]
        competencia = f"{ano}-{mes_numero:02d}-01"
        st.caption(f"Competência selecionada: **{mes_nome}/{ano}**")

        arquivo = st.file_uploader(
            "Arquivo mensal de produção *",
            type=["xlsx", "xls"],
            key="arquivo_producao_questor_contabit",
            help="Selecione o arquivo que contém os blocos Questor e Contabit.",
        )

        if arquivo is None:
            st.warning("Selecione o arquivo correspondente à competência informada.")
            return

        st.success("Arquivo selecionado.")
        st.write(f"**Arquivo:** {arquivo.name}")
        st.write(f"**Competência:** {mes_nome}/{ano}")

        st.divider()
        st.subheader("Validação do arquivo")

        try:
            df_questor, df_contabit = preparar_arquivo_producao(arquivo)
        except Exception as erro:
            st.error(f"Erro ao validar o arquivo: {erro}")
            return

        if df_questor.empty and df_contabit.empty:
            st.error("Nenhum cliente com movimentação foi encontrado.")
            return

        st.success("Arquivo validado e separado por origem com sucesso.")

        def resumo_bloco(df_bloco, titulo):
            st.markdown(f"#### {titulo}")
            if df_bloco.empty:
                st.info(f"Nenhuma movimentação encontrada para {titulo}.")
                return
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Clientes", formatar_numero(df_bloco["codigo_questor"].nunique()))
            c2.metric("Folha", formatar_numero(df_bloco["folha_pagamento"].sum()))
            c3.metric("Notas Fiscais", formatar_numero(df_bloco["notas_fiscais"].sum()))
            c4.metric("Contábil", formatar_numero(df_bloco["contabil"].sum()))
            c5.metric("Faturamento", formatar_moeda(df_bloco["faturamento"].sum()))

            if titulo == "Questor":
                st.caption(
                    f"Processos Questor: {formatar_numero(df_bloco['processos'].sum())}"
                )
            else:
                st.caption("Contabit não possui a coluna Processos neste layout.")

        resumo_bloco(df_questor, "Questor")
        resumo_bloco(df_contabit, "Contabit")

        # Consolidado apenas para conferência visual.
        codigos_consolidados = set(df_questor["codigo_questor"].astype(str))
        codigos_consolidados.update(df_contabit["codigo_questor"].astype(str))

        st.markdown("#### Consolidado para conferência")
        cc1, cc2, cc3, cc4, cc5 = st.columns(5)
        cc1.metric("Clientes únicos", formatar_numero(len(codigos_consolidados)))
        cc2.metric(
            "Folha",
            formatar_numero(
                df_questor["folha_pagamento"].sum() +
                df_contabit["folha_pagamento"].sum()
            ),
        )
        cc3.metric(
            "Notas Fiscais",
            formatar_numero(
                df_questor["notas_fiscais"].sum() +
                df_contabit["notas_fiscais"].sum()
            ),
        )
        cc4.metric(
            "Contábil",
            formatar_numero(
                df_questor["contabil"].sum() +
                df_contabit["contabil"].sum()
            ),
        )
        cc5.metric(
            "Faturamento",
            formatar_moeda(
                df_questor["faturamento"].sum() +
                df_contabit["faturamento"].sum()
            ),
        )

        st.divider()
        st.subheader("Pré-visualização")

        aba_q, aba_c = st.tabs(["Questor", "Contabit"])

        with aba_q:
            st.dataframe(df_questor, use_container_width=True, hide_index=True)

        with aba_c:
            st.dataframe(df_contabit, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Importação para o banco de dados")

        try:
            existentes_q = contar_registros_competencia(
                supabase, "Questor", competencia
            )
            existentes_c = contar_registros_competencia(
                supabase, "Contabit", competencia
            )
        except Exception as erro:
            st.error("Não foi possível consultar o banco de dados.")
            st.exception(erro)
            return

        st.write(
            f"Registros existentes em **{mes_nome}/{ano}** — "
            f"Questor: **{existentes_q}** | Contabit: **{existentes_c}**"
        )

        registros_q = preparar_registros_banco(
            df_questor, competencia, arquivo.name, "Questor"
        )
        registros_c = preparar_registros_banco(
            df_contabit, competencia, arquivo.name, "Contabit"
        )

        existe_algum = existentes_q > 0 or existentes_c > 0

        if existe_algum:
            st.warning(
                "Esta competência já possui dados. Para migrar para o novo padrão, "
                "a substituição apagará somente Questor e Contabit da competência "
                "selecionada e gravará novamente os dois blocos."
            )
            confirmar = st.checkbox(
                f"Confirmo a substituição completa de Questor + Contabit em {mes_nome}/{ano}.",
                key=f"confirmar_substituicao_dupla_{ano}_{mes_numero}",
            )
            texto_botao = f"Substituir {mes_nome}/{ano}"
        else:
            st.success("Esta competência ainda não possui dados Questor/Contabit.")
            confirmar = True
            texto_botao = f"Importar {mes_nome}/{ano}"

        if confirmar and st.button(
            texto_botao,
            type="primary",
            use_container_width=True,
        ):
            try:
                with st.spinner("Gravando Questor e Contabit separadamente..."):
                    if existe_algum:
                        excluir_competencia(supabase, "Questor", competencia)
                        excluir_competencia(supabase, "Contabit", competencia)

                    total_q = inserir_registros_em_lotes(supabase, registros_q) if registros_q else 0
                    total_c = inserir_registros_em_lotes(supabase, registros_c) if registros_c else 0

                st.success(
                    f"Importação concluída: {total_q} registros Questor + "
                    f"{total_c} registros Contabit."
                )
                st.balloons()
                st.rerun()

            except Exception as erro:
                st.error(
                    "A importação não foi concluída. Verifique a mensagem abaixo. "
                    "Se houve exclusão antes do erro, não importe outro mês até corrigirmos."
                )
                st.exception(erro)

