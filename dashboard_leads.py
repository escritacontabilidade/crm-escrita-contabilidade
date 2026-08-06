import pandas as pd
import streamlit as st


def calcular_indicadores_leads(supabase):
    """
    Calcula indicadores comerciais usando:
    - leads_externos
    - historico_vendas
    """

    res_leads = (
        supabase
        .table("leads_externos")
        .select("id,segmento,status,created_at,ativo")
        .execute()
    )

    res_historico = (
        supabase
        .table("historico_vendas")
        .select(
            "id,lead_id,segmento,status_comercial,"
            "data_apresentacao,data_fechamento,data_criacao"
        )
        .execute()
    )

    df_leads = pd.DataFrame(res_leads.data or [])
    df_historico = pd.DataFrame(res_historico.data or [])

    total_leads = len(df_leads)

    if df_historico.empty:
        return {
            "total_leads": total_leads,
            "total_convertidos": 0,
            "taxa_conversao": 0.0,
            "prazo_medio_dias": 0.0,
            "conversao_por_segmento": pd.DataFrame(),
        }

    if "status_comercial" not in df_historico.columns:
        df_historico["status_comercial"] = ""

    convertidos = df_historico[
        df_historico["status_comercial"] == "Contrato fechado"
    ].copy()

    total_convertidos = len(convertidos)

    taxa_conversao = (
        total_convertidos / total_leads * 100
        if total_leads > 0
        else 0.0
    )

    prazo_medio_dias = 0.0

    if (
        "data_apresentacao" in convertidos.columns
        and "data_fechamento" in convertidos.columns
        and not convertidos.empty
    ):
        convertidos["data_apresentacao"] = pd.to_datetime(
            convertidos["data_apresentacao"],
            errors="coerce",
        )

        convertidos["data_fechamento"] = pd.to_datetime(
            convertidos["data_fechamento"],
            errors="coerce",
        )

        convertidos = convertidos.dropna(
            subset=[
                "data_apresentacao",
                "data_fechamento",
            ]
        )

        if not convertidos.empty:
            convertidos["dias_ate_fechamento"] = (
                convertidos["data_fechamento"]
                - convertidos["data_apresentacao"]
            ).dt.days

            convertidos = convertidos[
                convertidos["dias_ate_fechamento"] >= 0
            ]

            if not convertidos.empty:
                prazo_medio_dias = float(
                    convertidos[
                        "dias_ate_fechamento"
                    ].mean()
                )

    if "segmento" not in df_historico.columns:
        df_historico["segmento"] = "Não informado"

    df_historico["segmento"] = (
        df_historico["segmento"]
        .fillna("Não informado")
        .replace("", "Não informado")
    )

    resumo_segmento = (
        df_historico
        .groupby("segmento", dropna=False)
        .agg(
            total_orcamentos=("id", "count"),
            convertidos=(
                "status_comercial",
                lambda serie: (
                    serie == "Contrato fechado"
                ).sum(),
            ),
        )
        .reset_index()
    )

    resumo_segmento["taxa_conversao"] = (
        resumo_segmento["convertidos"]
        / resumo_segmento["total_orcamentos"]
        * 100
    ).round(1)

    resumo_segmento = resumo_segmento.sort_values(
        "taxa_conversao",
        ascending=False,
    )

    resumo_segmento = resumo_segmento.rename(
        columns={
            "segmento": "Segmento",
            "total_orcamentos": "Orçamentos",
            "convertidos": "Convertidos",
            "taxa_conversao": "Taxa de conversão (%)",
        }
    )

    return {
        "total_leads": total_leads,
        "total_convertidos": total_convertidos,
        "taxa_conversao": taxa_conversao,
        "prazo_medio_dias": prazo_medio_dias,
        "conversao_por_segmento": resumo_segmento,
    }


def renderizar_dashboard_leads(supabase):
    """
    Exibe os indicadores comerciais na tela de Leads Recebidos.
    """

    try:
        indicadores = calcular_indicadores_leads(
            supabase
        )
    except Exception as erro:
        st.warning(
            "Não foi possível carregar os indicadores comerciais: "
            f"{erro}"
        )
        return

    coluna1, coluna2, coluna3, coluna4 = st.columns(4)

    coluna1.metric(
        "Leads recebidos",
        indicadores["total_leads"],
    )

    coluna2.metric(
        "Contratos fechados",
        indicadores["total_convertidos"],
    )

    coluna3.metric(
        "Taxa de conversão",
        f"{indicadores['taxa_conversao']:.1f}%",
    )

    coluna4.metric(
        "Prazo médio de conversão",
        f"{indicadores['prazo_medio_dias']:.1f} dias",
    )

    tabela_segmentos = indicadores[
        "conversao_por_segmento"
    ]

    if not tabela_segmentos.empty:
        st.markdown("### Conversão por segmento")

        st.dataframe(
            tabela_segmentos,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Taxa de conversão (%)": (
                    st.column_config.NumberColumn(
                        "Taxa de conversão (%)",
                        format="%.1f%%",
                    )
                ),
            },
        )

    st.caption(
        "Taxa de conversão: contratos fechados ÷ leads recebidos. "
        "Prazo médio: dias entre apresentação e fechamento."
    )
