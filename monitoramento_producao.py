import streamlit as st


def tela_monitoramento_producao(supabase):
    st.title("📊 Monitoramento de Produção")

    st.info(
        "Módulo para acompanhamento mensal da movimentação "
        "dos clientes da Escrita Contabilidade."
    )

    st.subheader("Importação da Produção")

    st.write(
        "Nesta área serão importados os arquivos mensais de produção "
        "extraídos do Questor."
    )

    st.file_uploader(
        "Selecione o arquivo de produção do Questor",
        type=["xlsx", "xls"],
        key="arquivo_producao_questor"
    )
