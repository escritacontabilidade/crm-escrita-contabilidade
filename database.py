import streamlit as st
from supabase import create_client


@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def fetch_table(table_name, select="*", order_by=None, desc=False):
    supabase = get_supabase()
    query = supabase.table(table_name).select(select)

    if order_by:
        query = query.order(order_by, desc=desc)

    return query.execute()


def insert_data(table_name, data):
    supabase = get_supabase()
    return supabase.table(table_name).insert(data).execute()


def upsert_data(table_name, data, on_conflict=None):
    supabase = get_supabase()
    if on_conflict:
        return supabase.table(table_name).upsert(data, on_conflict=on_conflict).execute()
    return supabase.table(table_name).upsert(data).execute()


def get_config_val(chave):
    supabase = get_supabase()
    res = supabase.table("configuracao_operacional").select("valor").eq("chave", chave).execute()

    if not res.data:
        raise ValueError(f"Configuração não encontrada: {chave}")

    return float(res.data[0]["valor"])


def get_peso_esforco(regime, item):
    supabase = get_supabase()
    res = (
        supabase
        .table("pesos_esforco")
        .select("horas_esforco")
        .eq("regime", regime)
        .eq("item", item)
        .execute()
    )

    if not res.data:
        raise ValueError(f"Peso de esforço não encontrado para regime='{regime}' e item='{item}'")

def get_origem_perguntas(segmentos_selecionados):
    """
    Recebe um segmento único (str) ou vários segmentos (list)
    e retorna a origem das perguntas.
    """
    supabase = get_supabase()

    if isinstance(segmentos_selecionados, list):
        segmentos_ordenados = sorted(segmentos_selecionados)
        chave = "+".join(segmentos_ordenados)
        tipo = "combinado"
    else:
        chave = segmentos_selecionados
        tipo = "simples"

    res = (
        supabase
        .table("regras_segmento")
        .select("origem_perguntas")
        .eq("tipo", tipo)
        .eq("segmentos", chave)
        .execute()
    )

    if not res.data:
        raise ValueError(f"Regra não encontrada para: {chave}")

    return res.data[0]["origem_perguntas"]


def get_perguntas_por_origem(origem):
    supabase = get_supabase()
    res = (
        supabase
        .table("perguntas")
        .select("*")
        .eq("origem", origem)
        .execute()
    )
    return res.data if res.data else []

    return float(res.data[0]["horas_esforco"])
