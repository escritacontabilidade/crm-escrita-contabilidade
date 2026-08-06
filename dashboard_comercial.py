import pandas as pd
import streamlit as st


def tela_dashboard_comercial(supabase):
    st.title("📊 Dashboard Comercial")

    try:
        leads = (
            supabase
            .table("leads_externos")
            .select("*")
            .execute()
            .data
            or []
        )

        orcamentos = (
            supabase
            .table("orcamentos")
            .select("*")
            .execute()
            .data
            or []
        )

        historico = (
            supabase
            .table("historico_vendas")
            .select("*")
            .execute()
            .data
            or []
        )

    except Exception as erro:
        st.error(
            "Não foi possível carregar os dados do dashboard: "
            f"{erro}"
        )
        return

    total_leads = len(leads)
    total_orcamentos = len(orcamentos)

    contratos_fechados = [
        item
        for item in historico
        if str(
            item.get("status_comercial") or ""
        ).strip() == "Contrato fechado"
    ]

    total_contratos = len(contratos_fechados)

    taxa_conversao = (
        total_contratos / total_leads * 100
        if total_leads > 0
        else 0
    )

    prazo_medio = 0.0

    df_fechados = pd.DataFrame(
        contratos_fechados
    )

    if not df_fechados.empty:
        if (
            "data_apresentacao" in df_fechados.columns
            and "data_fechamento" in df_fechados.columns
        ):
            df_fechados["data_apresentacao"] = pd.to_datetime(
                df_fechados["data_apresentacao"],
                errors="coerce",
            )

            df_fechados["data_fechamento"] = pd.to_datetime(
                df_fechados["data_fechamento"],
                errors="coerce",
            )

            df_fechados = df_fechados.dropna(
                subset=[
                    "data_apresentacao",
                    "data_fechamento",
                ]
            )

            if not df_fechados.empty:
                df_fechados["dias"] = (
                    df_fechados["data_fechamento"]
                    - df_fechados["data_apresentacao"]
                ).dt.days

                prazo_medio = float(
                    df_fechados["dias"].mean()
                )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Leads recebidos",
        total_leads,
    )

    c2.metric(
        "Orçamentos",
        total_orcamentos,
    )

    c3.metric(
        "Contratos fechados",
        total_contratos,
    )

    c4.metric(
        "Taxa de conversão",
        f"{taxa_conversao:.1f}%",
    )

    st.divider()

    esquerda, direita = st.columns(2)

    with esquerda:
        st.subheader("Funil comercial")

        df_funil = pd.DataFrame({
            "Etapa": [
                "Leads",
                "Orçamentos",
                "Contratos",
            ],
            "Quantidade": [
                total_leads,
                total_orcamentos,
                total_contratos,
            ],
        })

        st.bar_chart(
            df_funil.set_index("Etapa")
        )

    with direita:
        st.subheader("Prazo médio de conversão")

        st.metric(
            "Dias entre apresentação e fechamento",
            f"{prazo_medio:.1f} dias",
        )

    st.divider()

    if historico:
        df_historico = pd.DataFrame(
            historico
        )

        if (
            "segmento" in df_historico.columns
            and "status_comercial" in df_historico.columns
        ):
            resumo_segmento = (
                df_historico
                .groupby("segmento", dropna=False)
                .agg(
                    orcamentos=("id", "count"),
                    contratos=(
                        "status_comercial",
                        lambda serie: (
                            serie == "Contrato fechado"
                        ).sum(),
                    ),
                )
                .reset_index()
            )

            resumo_segmento[
                "taxa_conversao"
            ] = (
                resumo_segmento["contratos"]
                / resumo_segmento["orcamentos"]
                * 100
            ).round(1)

            resumo_segmento = (
                resumo_segmento
                .sort_values(
                    "taxa_conversao",
                    ascending=False,
                )
            )

            st.subheader(
                "Conversão por segmento"
            )

            st.bar_chart(
                resumo_segmento.set_index(
                    "segmento"
                )[["taxa_conversao"]]
            )

            st.dataframe(
                resumo_segmento.rename(
                    columns={
                        "segmento": "Segmento",
                        "orcamentos": "Orçamentos",
                        "contratos": "Contratos",
                        "taxa_conversao": (
                            "Taxa de conversão (%)"
                        ),
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
