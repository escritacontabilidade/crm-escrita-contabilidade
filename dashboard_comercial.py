import pandas as pd
import streamlit as st


STATUS_FECHADO = "Contrato fechado"


def _texto(valor):
    return str(valor or "").strip()


def _calcular_prazo_medio(df):
    """
    Calcula a média de dias entre apresentação e fechamento.
    Ignora registros sem as duas datas e intervalos negativos.
    """
    if df.empty:
        return 0.0

    if (
        "data_apresentacao" not in df.columns
        or "data_fechamento" not in df.columns
    ):
        return 0.0

    dados = df.copy()

    dados["data_apresentacao"] = pd.to_datetime(
        dados["data_apresentacao"],
        errors="coerce",
    )

    dados["data_fechamento"] = pd.to_datetime(
        dados["data_fechamento"],
        errors="coerce",
    )

    dados = dados.dropna(
        subset=[
            "data_apresentacao",
            "data_fechamento",
        ]
    )

    if dados.empty:
        return 0.0

    dados["dias_ate_fechamento"] = (
        dados["data_fechamento"]
        - dados["data_apresentacao"]
    ).dt.days

    dados = dados[
        dados["dias_ate_fechamento"] >= 0
    ]

    if dados.empty:
        return 0.0

    return float(
        dados["dias_ate_fechamento"].mean()
    )


def _montar_indicadores_segmento(
    df_historico,
):
    """
    Monta indicadores comerciais por segmento.
    """

    if df_historico.empty:
        return pd.DataFrame()

    if (
        "segmento" not in df_historico.columns
        or "status_comercial" not in df_historico.columns
    ):
        return pd.DataFrame()

    dados = df_historico.copy()

    dados["segmento"] = (
        dados["segmento"]
        .fillna("Não informado")
        .astype(str)
        .str.strip()
        .replace("", "Não informado")
    )

    linhas = []

    for segmento, grupo in dados.groupby(
        "segmento",
        dropna=False,
    ):
        total = len(grupo)

        fechados = grupo[
            grupo["status_comercial"]
            .fillna("")
            .astype(str)
            .str.strip()
            == STATUS_FECHADO
        ].copy()

        total_fechados = len(fechados)

        taxa = (
            total_fechados / total * 100
            if total > 0
            else 0.0
        )

        prazo = _calcular_prazo_medio(
            fechados
        )

        linhas.append({
            "Segmento": segmento,
            "Oportunidades": total,
            "Contratos fechados": total_fechados,
            "Taxa de conversão (%)": round(
                taxa,
                1,
            ),
            "Prazo médio (dias)": round(
                prazo,
                1,
            ),
        })

    resultado = pd.DataFrame(
        linhas
    )

    if resultado.empty:
        return resultado

    return resultado.sort_values(
        [
            "Taxa de conversão (%)",
            "Contratos fechados",
        ],
        ascending=[
            False,
            False,
        ],
    )


def tela_dashboard_comercial(
    supabase,
):
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
            "Não foi possível carregar os dados "
            "do dashboard: "
            f"{erro}"
        )
        return

    # =========================================================
    # INDICADORES GERAIS
    # =========================================================

    total_leads = len(leads)

    total_orcamentos = len(
        orcamentos
    )

    contratos_fechados = [
        item
        for item in historico
        if _texto(
            item.get(
                "status_comercial"
            )
        ) == STATUS_FECHADO
    ]

    total_contratos = len(
        contratos_fechados
    )

    taxa_conversao = (
        total_contratos
        / total_leads
        * 100
        if total_leads > 0
        else 0.0
    )

    df_fechados = pd.DataFrame(
        contratos_fechados
    )

    prazo_medio = (
        _calcular_prazo_medio(
            df_fechados
        )
    )

    # =========================================================
    # CARDS
    # =========================================================

    c1, c2, c3, c4, c5 = (
        st.columns(5)
    )

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

    c5.metric(
        "Prazo médio",
        f"{prazo_medio:.1f} dias",
    )

    st.caption(
        "Taxa de conversão = contratos fechados ÷ "
        "leads recebidos. Prazo médio = dias entre "
        "apresentação da proposta e fechamento."
    )

    st.divider()

    # =========================================================
    # FUNIL
    # =========================================================

    st.subheader(
        "Funil comercial"
    )

    df_funil = pd.DataFrame({
        "Etapa": [
            "Leads recebidos",
            "Orçamentos",
            "Contratos fechados",
        ],
        "Quantidade": [
            total_leads,
            total_orcamentos,
            total_contratos,
        ],
    })

    st.bar_chart(
        df_funil.set_index(
            "Etapa"
        )
    )

    st.divider()

    # =========================================================
    # INDICADORES POR SEGMENTO
    # =========================================================

    st.subheader(
        "Índices por setor / segmento"
    )

    if not historico:
        st.info(
            "Ainda não existem dados no histórico "
            "de vendas para calcular os índices "
            "por segmento."
        )
        return

    df_historico = pd.DataFrame(
        historico
    )

    resumo_segmento = (
        _montar_indicadores_segmento(
            df_historico
        )
    )

    if resumo_segmento.empty:
        st.info(
            "Não foi possível calcular os "
            "indicadores por segmento."
        )
        return

    # =========================================================
    # GRÁFICO DE CONVERSÃO
    # =========================================================

    st.markdown(
        "#### Taxa de conversão por segmento"
    )

    grafico_conversao = (
        resumo_segmento[
            [
                "Segmento",
                "Taxa de conversão (%)",
            ]
        ]
        .set_index(
            "Segmento"
        )
    )

    st.bar_chart(
        grafico_conversao
    )

    # =========================================================
    # TABELA COMPLETA
    # =========================================================

    st.markdown(
        "#### Desempenho comercial por segmento"
    )

    st.dataframe(
        resumo_segmento,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Taxa de conversão (%)": (
                st.column_config.NumberColumn(
                    "Taxa de conversão (%)",
                    format="%.1f%%",
                )
            ),
            "Prazo médio (dias)": (
                st.column_config.NumberColumn(
                    "Prazo médio (dias)",
                    format="%.1f",
                )
            ),
        },
    )

    # =========================================================
    # DESTAQUES
    # =========================================================

    segmentos_com_venda = (
        resumo_segmento[
            resumo_segmento[
                "Contratos fechados"
            ] > 0
        ]
    )

    if not segmentos_com_venda.empty:
        melhor = (
            segmentos_com_venda.iloc[0]
        )

        st.success(
            "Melhor taxa de conversão: "
            f"{melhor['Segmento']} — "
            f"{melhor['Taxa de conversão (%)']:.1f}% "
            f"({int(melhor['Contratos fechados'])} "
            "contrato(s) fechado(s))."
        )

    st.caption(
        "Os indicadores utilizam os dados registrados "
        "no histórico comercial. Segmentos sem fechamento "
        "permanecem com taxa de conversão igual a 0%."
    )
