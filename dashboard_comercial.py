import streamlit as st
import pandas as pd


def tela_dashboard_comercial(supabase):

    st.title("📊 Dashboard Comercial")

    # =============================
    # CONSULTAS
    # =============================

    leads = supabase.table("leads").select("*").execute().data

    propostas = (
        supabase
        .table("propostas")
        .select("*")
        .execute()
        .data
    )

    historico = (
        supabase
        .table("historico_vendas")
        .select("*")
        .execute()
        .data
    )

    total_leads = len(leads)
    total_propostas = len(propostas)
    contratos = len(
        [x for x in historico if x.get("status") == "Fechado"]
    )

    conversao = 0

    if total_leads:
        conversao = contratos / total_leads * 100

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Leads", total_leads)
    c2.metric("Propostas", total_propostas)
    c3.metric("Contratos", contratos)
    c4.metric("Conversão", f"{conversao:.1f}%")

    st.divider()

    st.subheader("Funil Comercial")

    df = pd.DataFrame(
        {
            "Etapa": [
                "Leads",
                "Propostas",
                "Contratos",
            ],
            "Quantidade": [
                total_leads,
                total_propostas,
                contratos,
            ],
        }
    )

    st.bar_chart(df.set_index("Etapa"))
