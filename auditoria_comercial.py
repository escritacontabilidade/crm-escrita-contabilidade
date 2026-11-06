"""Auditoria comercial somente leitura: leads, orçamentos e pipeline."""
from collections import defaultdict
from datetime import datetime, timezone
import pandas as pd
import streamlit as st


def _buscar_todos(supabase, tabela):
    itens = []
    inicio = 0
    while True:
        lote = (supabase.table(tabela).select('*').range(inicio, inicio + 999).execute().data or [])
        itens.extend(lote)
        if len(lote) < 1000:
            return itens
        inicio += 1000


def _id(valor):
    if valor is None or str(valor).strip() in ('', 'nan', 'None'):
        return None
    try:
        return int(valor)
    except (ValueError, TypeError):
        return None


def _ativo(reg):
    return reg.get('ativo') is not False and not reg.get('deleted_at')


def _dias(data):
    try:
        dt = pd.to_datetime(data, utc=True)
        if pd.isna(dt):
            return None
        return max(0, (datetime.now(timezone.utc) - dt.to_pydatetime()).days)
    except (ValueError, TypeError, OverflowError):
        return None


def auditar(leads, orcamentos, historicos):
    """Não faz gravações. Nunca equipara clientes apenas pelo nome."""
    leads = [x for x in leads if _ativo(x)]
    orcamentos_ativos = [x for x in orcamentos if _ativo(x)]
    historicos_ativos = [x for x in historicos if _ativo(x)]
    por_lead_orc, por_lead_hist, por_orc_hist = defaultdict(list), defaultdict(list), defaultdict(list)
    por_id_orc = {_id(x.get('id')): x for x in orcamentos}
    for o in orcamentos_ativos:
        if _id(o.get('lead_id')) is not None:
            por_lead_orc[_id(o.get('lead_id'))].append(o)
    for h in historicos_ativos:
        if _id(h.get('lead_id')) is not None:
            por_lead_hist[_id(h.get('lead_id'))].append(h)
        if _id(h.get('orcamento_id')) is not None:
            por_orc_hist[_id(h.get('orcamento_id'))].append(h)

    linhas = []
    for lead in leads:
        lid = _id(lead.get('id'))
        os = por_lead_orc[lid]
        hs = por_lead_hist[lid]
        dias = _dias(lead.get('created_at'))
        faltas = []
        if not hs:
            faltas.append('Sem registro ativo no Pipeline')
        if not os:
            faltas.append('Sem orçamento vinculado ao lead')
        if not (lead.get('whatsapp') or lead.get('telefone') or lead.get('email')):
            faltas.append('Sem contato informado')
        if any(not h.get('responsavel') for h in hs):
            faltas.append('Pipeline sem responsável')
        if not hs and dias is not None and dias >= 2:
            faltas.append('Lead há 2+ dias sem Pipeline')
        linhas.append({
            'Origem': 'Lead', 'Lead ID': lid, 'Orçamento ID': ', '.join(str(o['id']) for o in os),
            'Histórico ID': ', '.join(str(h['id']) for h in hs),
            'Empresa': lead.get('nome_empresa') or '(sem nome)',
            'Dias desde recebimento': dias, 'Status lead': lead.get('status') or '',
            'Status pipeline': ', '.join(str(h.get('status_comercial') or 'Em aberto') for h in hs),
            'Situação': '; '.join(faltas) if faltas else 'Sem alerta estrutural',
            'Tipo': 'Pendente' if faltas else 'Regular'
        })

    for o in orcamentos_ativos:
        oid = _id(o.get('id'))
        hs = por_orc_hist[oid]
        if not hs:
            linhas.append({
                'Origem': 'Orçamento', 'Lead ID': _id(o.get('lead_id')),
                'Orçamento ID': str(oid), 'Histórico ID': '',
                'Empresa': o.get('cliente') or '(sem nome)',
                'Dias desde recebimento': _dias(o.get('created_at')),
                'Status lead': '', 'Status pipeline': '',
                'Situação': 'Orçamento ativo sem histórico ativo vinculado por orcamento_id',
                'Tipo': 'Pendente'
            })
    for h in historicos_ativos:
        oid = _id(h.get('orcamento_id'))
        if oid is not None and oid not in por_id_orc:
            motivo = 'Histórico aponta para orçamento inexistente'
        elif oid is not None and not _ativo(por_id_orc[oid]):
            motivo = 'Histórico ativo vinculado a orçamento inativo'
        elif oid is None:
            motivo = 'Pipeline sem orçamento (pode ser etapa pré-proposta)'
        else:
            continue
        linhas.append({
            'Origem': 'Pipeline', 'Lead ID': _id(h.get('lead_id')),
            'Orçamento ID': str(oid) if oid is not None else '',
            'Histórico ID': str(h.get('id')), 'Empresa': h.get('cliente') or '(sem nome)',
            'Dias desde recebimento': _dias(h.get('data_criacao')),
            'Status lead': '', 'Status pipeline': h.get('status_comercial') or 'Em aberto',
            'Situação': motivo, 'Tipo': 'Verificar' if oid is None else 'Pendente'
        })
    return pd.DataFrame(linhas)


def tela_auditoria_comercial(supabase):
    st.title('Auditoria Comercial')
    st.caption('Conciliação somente leitura. Nenhum lead, orçamento ou histórico será modificado.')
    st.warning('Ausência de orçamento não significa, por si só, falha: o lead pode estar em atendimento. Alertas exigem conferência humana.')
    if st.button('Atualizar auditoria', type='primary'):
        st.rerun()
    try:
        leads = _buscar_todos(supabase, 'leads_externos')
        orcamentos = _buscar_todos(supabase, 'orcamentos')
        historicos = _buscar_todos(supabase, 'historico_vendas')
        df = auditar(leads, orcamentos, historicos)
    except Exception as exc:
        st.error(f'Não foi possível consultar os registros: {exc}')
        return
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Leads ativos', sum(_ativo(x) for x in leads))
    c2.metric('Orçamentos ativos', sum(_ativo(x) for x in orcamentos))
    c3.metric('Pipeline ativo', sum(_ativo(x) for x in historicos))
    c4.metric('Alertas e verificações', int((df['Tipo'] != 'Regular').sum()) if not df.empty else 0)
    if df.empty:
        st.info('Nenhum registro encontrado para auditoria.')
        return
    tipo = st.selectbox('Filtrar situação', ['Todos', 'Pendente', 'Verificar', 'Regular'])
    if tipo != 'Todos':
        df = df[df['Tipo'] == tipo]
    busca = st.text_input('Buscar empresa ou ID')
    if busca.strip():
        texto = busca.strip().casefold()
        df = df[df.astype(str).apply(lambda col: col.str.casefold().str.contains(texto, regex=False)).any(axis=1)]
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button('Exportar auditoria (CSV)', df.to_csv(index=False, sep=';').encode('utf-8-sig'),
                       file_name='auditoria_comercial.csv', mime='text/csv')
    st.caption('A auditoria não identifica movimentações ou próximos contatos: as três tabelas não possuem histórico completo de atividades e prazos.')
