import streamlit as st
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

    # ---------------------------------------------------------
    # COMPETÊNCIA
    # ---------------------------------------------------------

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

    st.caption(
        f"Competência selecionada: **{mes_nome}/{ano}**"
    )

    # ---------------------------------------------------------
    # SISTEMA
    # ---------------------------------------------------------

    st.text_input(
        "Sistema de origem",
        value="Questor",
        disabled=True,
        key="producao_sistema_origem",
    )

    # ---------------------------------------------------------
    # ARQUIVO
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # RESUMO ANTES DA IMPORTAÇÃO
    # ---------------------------------------------------------

    st.success("Arquivo selecionado.")

    st.write(f"**Arquivo:** {arquivo.name}")
    st.write("**Sistema:** Questor")
    st.write(f"**Competência:** {mes_nome}/{ano}")

    st.divider()

    st.warning(
        "A importação ainda não está habilitada nesta etapa. "
        "Primeiro vamos validar a leitura e a estrutura do arquivo "
        "antes de permitir qualquer gravação no banco de dados."
    )
