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
        return 0.0

    valor = res.data[0].get("valor")

    if valor is None:
        return 0.0

    return float(valor)


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
        return 0.0

    valor = res.data[0].get("horas_esforco")

    if valor is None:
        return 0.0

    return float(valor)

def get_origem_perguntas(segmento_escolhido):
    supabase = get_supabase()

    res = (
        supabase
        .table("regras_segmento")
        .select("origem_perguntas")
        .eq("segmentos", segmento_escolhido)
        .execute()
    )

    if not res.data:
        raise ValueError(f"Regra não encontrada para: {segmento_escolhido}")

    return res.data[0]["origem_perguntas"]


def get_perguntas_por_origem(origem):
    supabase = get_supabase()
    res = (
        supabase
        .table("perguntas")
        .select("*")
        .eq("origem", origem)
        .order("ordem")
        .order("id")
        .execute()
    )
    return res.data if res.data else []

    
def get_regras_precificacao():
    supabase = get_supabase()

    res = (
        supabase
        .table("regras_perguntas_precificacao")
        .select("*")
        .eq("ativo", True)
        .execute()
    )

    return res.data if res.data else []


@st.cache_data(ttl=300)
def get_faixas_precificacao():
    supabase = get_supabase()

    res = (
        supabase
        .table("faixas_precificacao")
        .select("*")
        .eq("ativo", True)
        .order("regra_pergunta_id")
        .order("ordem")
        .execute()
    )

    if not res.data:
        return {}

    faixas = {}

    for linha in res.data:
        regra_id = int(linha["regra_pergunta_id"])

        if regra_id not in faixas:
            faixas[regra_id] = []

        faixas[regra_id].append(linha)

    return faixas

def criar_backup_precificacao(
    supabase,
    nome,
    descricao="",
    tipo="manual",
    percentual_reajuste=None,
    criado_por="Sistema"
):
    """
    Cria um snapshot completo da precificação.
    """

    precos = supabase.table(
        "precos_base_precificacao"
    ).select("*").execute().data

    regras = supabase.table(
        "regras_perguntas_precificacao"
    ).select("*").execute().data

    faixas = supabase.table(
        "faixas_precificacao"
    ).select("*").execute().data

    dados = {
        "nome": nome,
        "descricao": descricao,
        "tipo": tipo,
        "percentual_reajuste": percentual_reajuste,

        "snapshot_precos_base": precos,
        "snapshot_regras": regras,
        "snapshot_faixas": faixas,

        "quantidade_precos_base": len(precos),
        "quantidade_regras": len(regras),
        "quantidade_faixas": len(faixas),

        "criado_por": criado_por
    }

    return (
        supabase
        .table("precificacao_versoes")
        .insert(dados)
        .execute()
    )

@st.cache_data(ttl=60)
def listar_versoes_precificacao(_supabase):
    """
    Retorna todas as versões de precificação,
    da mais recente para a mais antiga.

    O underline em _supabase impede que o Streamlit
    tente calcular o hash do cliente Supabase.
    """

    resultado = (
        _supabase
        .table("precificacao_versoes")
        .select(
            "id,nome,descricao,tipo,percentual_reajuste,"
            "quantidade_precos_base,"
            "quantidade_regras,"
            "quantidade_faixas,"
            "criado_por,"
            "criado_em,"
            "restaurada_em"
        )
        .order("criado_em", desc=True)
        .execute()
    )

    return resultado.data or []

@st.cache_data(ttl=60)
def obter_versao_precificacao(_supabase, versao_id):
    """
    Retorna uma versão completa da precificação.

    O underline em _supabase impede que o Streamlit
    tente calcular o hash do cliente Supabase.
    """

    resultado = (
        _supabase
        .table("precificacao_versoes")
        .select("*")
        .eq("id", int(versao_id))
        .single()
        .execute()
    )

    return resultado.data
