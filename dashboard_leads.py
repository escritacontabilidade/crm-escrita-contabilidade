"""Indicadores da tela Leads Recebidos — CRM Escrita Contabilidade.

Somente registros ativos; oportunidades com orçamento inexistente/arquivado
ou lead vinculado inexistente/arquivado não compõem os indicadores.
"""
import pandas as pd
import streamlit as st

STATUS_FECHADO = "Contrato fechado"
STATUS_APRESENTADOS = {"Preço apresentado", "Contrato fechado", "Negativa", "Sem resposta"}


def _ativo(registro):
    valor = registro.get("ativo", True)
    return valor is not False and str(valor).strip().lower() not in ("false", "0", "não", "nao")


def _id(valor):
    return "" if valor is None else str(valor).strip()


def _segmento(valor):
    texto = str(valor or "").strip()
    return texto or "Não informado"


def _prazo_medio(fechados):
    if not fechados:
        return None
    df = pd.DataFrame(fechados)
    if not {"data_apresentacao", "data_fechamento"}.issubset(df.columns):
        return None
    apresentacao = pd.to_datetime(df["data_apresentacao"], errors="coerce", utc=True)
    fechamento = pd.to_datetime(df["data_fechamento"], errors="coerce", utc=True)
    dias = (fechamento - apresentacao).dt.days
    dias = dias[dias.notna() & (dias >= 0)]
    return float(dias.mean()) if not dias.empty else None


def calcular_indicadores_leads(supabase):
    leads = supabase.table("leads_externos").select("*").execute().data or []
    orcamentos = supabase.table("orcamentos").select("*").execute().data or []
    historico = supabase.table("historico_vendas").select("*").execute().data or []

    leads_ativos = [item for item in leads if _ativo(item)]
    orcamentos_ativos = [item for item in orcamentos if _ativo(item)]
    ids_leads_ativos = {_id(item.get("id")) for item in leads_ativos}
    ids_orcamentos_ativos = {_id(item.get("id")) for item in orcamentos_ativos}

    def elegivel(item):
        if not _ativo(item):
            return False
        # A oportunidade comercial precisa ter orçamento existente e ativo.
        orcamento_id = _id(item.get("orcamento_id"))
        if not orcamento_id or orcamento_id not in ids_orcamentos_ativos:
            return False
        # O vínculo com lead é opcional, mas, se existir, precisa ser válido.
        lead_id = _id(item.get("lead_id"))
        if lead_id and lead_id not in ids_leads_ativos:
            return False
        return True

    oportunidades = [item for item in historico if elegivel(item)]
    fechados = [item for item in oportunidades if str(item.get("status_comercial") or "").strip() == STATUS_FECHADO]
    apresentados = [item for item in oportunidades if (
        str(item.get("status_comercial") or "").strip() in STATUS_APRESENTADOS
        or bool(item.get("data_apresentacao"))
    )]

    total_leads = len(leads_ativos)
    total_orcamentos = len(orcamentos_ativos)
    total_fechados = len(fechados)
    total_apresentados = len(apresentados)
    conversao_leads = total_fechados / total_leads * 100 if total_leads else 0.0
    conversao_comercial = total_fechados / total_apresentados * 100 if total_apresentados else 0.0

    por_segmento = {}
    for item in orcamentos_ativos:
        seg = _segmento(item.get("segmento"))
        por_segmento.setdefault(seg, {"Orçamentos": 0, "Apresentados": 0, "Convertidos": 0})["Orçamentos"] += 1
    for item in apresentados:
        seg = _segmento(item.get("segmento"))
        por_segmento.setdefault(seg, {"Orçamentos": 0, "Apresentados": 0, "Convertidos": 0})["Apresentados"] += 1
    for item in fechados:
        seg = _segmento(item.get("segmento"))
        por_segmento.setdefault(seg, {"Orçamentos": 0, "Apresentados": 0, "Convertidos": 0})["Convertidos"] += 1

    linhas = []
    for segmento, valores in por_segmento.items():
        denominador = valores["Apresentados"]
        linhas.append({
            "Segmento": segmento,
            **valores,
            "Taxa de conversão (%)": round(valores["Convertidos"] / denominador * 100, 1) if denominador else 0.0,
        })
    resumo = pd.DataFrame(linhas, columns=["Segmento", "Orçamentos", "Apresentados", "Convertidos", "Taxa de conversão (%)"])
    if not resumo.empty:
        resumo = resumo.sort_values(["Taxa de conversão (%)", "Convertidos"], ascending=[False, False])

    return {
        "total_leads": total_leads,
        "total_orcamentos": total_orcamentos,
        "total_apresentados": total_apresentados,
        "total_convertidos": total_fechados,
        "taxa_conversao": conversao_leads,
        "taxa_conversao_comercial": conversao_comercial,
        "prazo_medio_dias": _prazo_medio(fechados),
        "conversao_por_segmento": resumo,
    }


def renderizar_dashboard_leads(supabase):
    """Renderiza indicadores sem modificar dados ou a tela de listagem de leads."""
    try:
        indicadores = calcular_indicadores_leads(supabase)
    except Exception as erro:
        st.warning(f"Não foi possível carregar os indicadores comerciais: {erro}")
        return

    colunas = st.columns(5)
    colunas[0].metric("Leads recebidos", indicadores["total_leads"])
    colunas[1].metric("Contratos fechados", indicadores["total_convertidos"])
    colunas[2].metric("Conversão de leads", f'{indicadores["taxa_conversao"]:.1f}%')
    colunas[3].metric("Conversão comercial", f'{indicadores["taxa_conversao_comercial"]:.1f}%')
    prazo = indicadores["prazo_medio_dias"]
    colunas[4].metric("Prazo médio de conversão", f"{prazo:.1f} dias" if prazo is not None else "N/D")

    tabela = indicadores["conversao_por_segmento"]
    if not tabela.empty:
        st.markdown("### Conversão por segmento")
        st.dataframe(
            tabela, use_container_width=True, hide_index=True,
            column_config={"Taxa de conversão (%)": st.column_config.NumberColumn(
                "Taxa de conversão (%)", format="%.1f%%")},
        )

    st.caption(
        "Conversão de leads: contratos fechados ÷ leads ativos. "
        "Conversão comercial: contratos fechados ÷ propostas apresentadas. "
        "Prazo médio: dias entre apresentação e fechamento (somente datas válidas). "
        "Arquivados e vínculos inválidos são desconsiderados."
    )
