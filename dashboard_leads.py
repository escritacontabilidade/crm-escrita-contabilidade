import pandas as pd
import streamlit as st


STATUS_FECHADO = "Contrato fechado"


def calcular_indicadores_leads(supabase):
    """
    Calcula indicadores comerciais usando:
    - leads_externos
    - orcamentos ativos
    - historico_vendas
    """

    res_leads = (
        supabase
        .table("leads_externos")
        .select("id,segmento,status,created_at,ativo")
        .execute()
    )

    res_orcamentos = (
        supabase
        .table("orcamentos")
        .select("id,segmento,ativo")
        .eq("ativo", True)
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
    df_orcamentos = pd.DataFrame(res_orcamentos.data or [])
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
        df_historico["status_comercial"] == STATUS_FECHADO
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

    # =========================================================
    # ORÇAMENTOS ATIVOS POR SEGMENTO
    # =========================================================

    if df_orcamentos.empty:
        resumo_orcamentos = pd.DataFrame(
            columns=[
                "Segmento",
                "Orçamentos",
            ]
        )
    else:
        if "segmento" not in df_orcamentos.columns:
            df_orcamentos["segmento"] = "Não informado"

        df_orcamentos["segmento"] = (
            df_orcamentos["segmento"]
            .fillna("Não informado")
            .astype(str)
            .str.strip()
            .replace("", "Não informado")
        )

        resumo_orcamentos = (
            df_orcamentos
            .groupby(
                "segmento",
                dropna=False,
            )
            .agg(
                Orçamentos=("id", "count")
            )
            .reset_index()
            .rename(
                columns={
                    "segmento": "Segmento",
                }
            )
        )

    # =========================================================
    # CONVERTIDOS POR SEGMENTO
    # =========================================================

    if convertidos.empty:
        resumo_convertidos = pd.DataFrame(
            columns=[
                "Segmento",
                "Convertidos",
            ]
        )
    else:
        if "segmento" not in convertidos.columns:
            convertidos["segmento"] = "Não informado"

        convertidos["segmento"] = (
            convertidos["segmento"]
            .fillna("Não informado")
            .astype(str)
            .str.strip()
            .replace("", "Não informado")
        )

        resumo_convertidos = (
            convertidos
            .groupby(
                "segmento",
                dropna=False,
            )
            .agg(
                Convertidos=("id", "count")
            )
            .reset_index()
            .rename(
                columns={
                    "segmento": "Segmento",
                }
            )
        )

    # =========================================================
    # JUNTA ORÇAMENTOS + CONVERTIDOS
    # =========================================================

    resumo_segmento = pd.merge(
        resumo_orcamentos,
        resumo_convertidos,
        on="Segmento",
        how="outer",
    )

    if resumo_segmento.empty:
        return {
            "total_leads": total_leads,
            "total_convertidos": total_convertidos,
            "taxa_conversao": taxa_conversao,
            "prazo_medio_dias": prazo_medio_dias,
            "conversao_por_segmento": pd.DataFrame(),
        }

    resumo_segmento["Orçamentos"] = (
        resumo_segmento["Orçamentos"]
        .fillna(0)
        .astype(int)
    )

    resumo_segmento["Convertidos"] = (
        resumo_segmento["Convertidos"]
        .fillna(0)
        .astype(int)
    )

    resumo_segmento["Taxa de conversão (%)"] = (
        resumo_segmento.apply(
            lambda linha: (
                linha["Convertidos"]
                / linha["Orçamentos"]
                * 100
                if linha["Orçamentos"] > 0
                else 0.0
            ),
            axis=1,
        )
    ).round(1)

    resumo_segmento = resumo_segmento.sort_values(
        [
            "Taxa de conversão (%)",
            "Convertidos",
        ],
        ascending=[
            False,
            False,
        ],
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
