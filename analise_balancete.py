import streamlit as st


def tela_analise_balancete(supabase):
    st.title("📊 Análise do Balancete")

    lead = st.session_state.get("lead_balancete")
    arquivo = st.session_state.get("arquivo_balancete")

    if lead is None:
        st.warning(
            "Nenhum cliente foi selecionado."
        )
        return

    st.success("Cliente carregado com sucesso.")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Empresa",
            lead.get("nome_empresa", "-")
        )

    with col2:
        st.metric(
            "CNPJ",
            lead.get("cnpj", "-")
        )

    st.divider()

    st.subheader("Arquivo do balancete")

    if arquivo:
        st.write(
            f"**Nome:** {arquivo.get('nome_arquivo','-')}"
        )

        st.write(
            f"**Tipo:** {arquivo.get('mime_type','-')}"
        )

        st.write(
            f"**Link:** {arquivo.get('drive_link','-')}"
        )

    else:
        st.warning(
            "Este cliente não possui balancete anexado."
        )

    st.divider()

    st.subheader("Análises")

    st.info(
        "Em desenvolvimento."
    )
