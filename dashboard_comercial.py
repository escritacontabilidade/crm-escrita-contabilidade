"""Dashboard comercial da Escrita Contabilidade.

Apuração por eventos (datas de criação/apresentação/fechamento) e exclusão
integral de registros arquivados, inclusive nos períodos históricos.
"""
from datetime import date, timedelta
import calendar
import pandas as pd
import streamlit as st

STATUS_FECHADO = 'Contrato fechado'
STATUS_APRESENTADO = {'Preço apresentado', 'Contrato fechado', 'Negativa', 'Sem resposta'}
MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
         'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']


def _texto(valor):
    return '' if valor is None else str(valor).strip()


def _ativo(item):
    valor = item.get('ativo', True)
    return valor is not False and _texto(valor).lower() not in ('false', '0', 'não', 'nao')


def _data(item, campos):
    for campo in campos:
        valor = item.get(campo)
        if valor is None or _texto(valor) == '':
            continue
        dt = pd.to_datetime(valor, errors='coerce', utc=True)
        if pd.notna(dt):
            return dt.date()
    return None


def _no_periodo(dt, inicio, fim):
    if inicio is None and fim is None:
        return True
    return dt is not None and inicio <= dt <= fim


def _datas_periodo():
    st.subheader('Período de análise')
    opcoes = ['Todo o período', 'Mês', 'Bimestre', 'Trimestre', 'Quadrimestre',
              'Semestre', 'Ano', 'Personalizado']
    c1, c2, c3 = st.columns([1.5, 1, 1.4])
    with c1:
        tipo = st.selectbox('Agrupamento', opcoes, key='dashboard_periodo_tipo')
    if tipo == 'Todo o período':
        return None, None, 'Todo o período'
    hoje = date.today()
    if tipo == 'Personalizado':
        with c2:
            inicio = st.date_input('Data inicial', value=date(hoje.year, 1, 1),
                                   key='dashboard_data_inicio')
        with c3:
            fim = st.date_input('Data final', value=hoje,
                                key='dashboard_data_fim')
        if inicio > fim:
            st.error('A data inicial não pode ser posterior à data final.')
            st.stop()
        return inicio, fim, f'{inicio:%d/%m/%Y} a {fim:%d/%m/%Y}'
    with c2:
        ano = st.number_input('Ano', min_value=2000, max_value=2100,
                              value=hoje.year, step=1, key='dashboard_ano')
    if tipo == 'Ano':
        return date(ano, 1, 1), date(ano, 12, 31), str(ano)
    meses_por_periodo = {'Mês': 1, 'Bimestre': 2, 'Trimestre': 3,
                         'Quadrimestre': 4, 'Semestre': 6}
    n = meses_por_periodo[tipo]
    opcoes_periodos = list(range(1, 13, n))
    with c3:
        indice = st.selectbox(
            tipo, opcoes_periodos,
            format_func=lambda m: MESES[m-1] if n == 1 else
            f'{MESES[m-1]} a {MESES[m+n-2]}',
            index=min((hoje.month-1)//n, len(opcoes_periodos)-1),
            key='dashboard_periodo_indice',
        )
    ultimo = indice + n - 1
    inicio = date(ano, indice, 1)
    fim = date(ano, ultimo, calendar.monthrange(ano, ultimo)[1])
    return inicio, fim, f'{MESES[indice-1]} a {MESES[ultimo-1]} / {ano}'


def _calcular_prazo_medio(df):
    if df.empty or not {'data_apresentacao', 'data_fechamento'}.issubset(df.columns):
        return None
    datas = df[['data_apresentacao', 'data_fechamento']].copy()
    for campo in datas.columns:
        datas[campo] = pd.to_datetime(datas[campo], errors='coerce', utc=True)
    dias = (datas['data_fechamento'] - datas['data_apresentacao']).dt.days
    dias = dias[(dias >= 0) & dias.notna()]
    return float(dias.mean()) if not dias.empty else None


def _montar_indicadores_segmento(df_historico, inicio=None, fim=None):
    if df_historico.empty:
        return pd.DataFrame()
    dados = df_historico.copy()
    dados['segmento'] = dados.get('segmento', pd.Series('Não informado', index=dados.index))
    dados['segmento'] = dados['segmento'].fillna('Não informado').astype(str).str.strip().replace('', 'Não informado')
    linhas = []
    for segmento, grupo in dados.groupby('segmento', dropna=False):
        # Coorte: oportunidades criadas no período; fechamento no mesmo grupo.
        grupo_coorte = grupo[grupo.apply(lambda r: _no_periodo(
            _data(r, ['data_criacao', 'created_at']), inicio, fim), axis=1)]
        fechados = grupo_coorte[grupo_coorte['status_comercial'] == STATUS_FECHADO]
        total = len(grupo_coorte)
        linhas.append({
            'Segmento': segmento, 'Oportunidades': total,
            'Contratos fechados': len(fechados),
            'Taxa de conversão (%)': round(len(fechados) / total * 100, 1) if total else 0.0,
            'Prazo médio (dias)': _calcular_prazo_medio(fechados),
        })
    resultado = pd.DataFrame(linhas)
    return resultado[resultado['Oportunidades'] > 0].sort_values(
        ['Taxa de conversão (%)', 'Contratos fechados'], ascending=[False, False])


def tela_dashboard_comercial(supabase):
    st.title('📊 Dashboard Comercial')
    try:
        leads = supabase.table('leads_externos').select('*').execute().data or []
        orcamentos = supabase.table('orcamentos').select('*').execute().data or []
        historico = supabase.table('historico_vendas').select('*').execute().data or []
    except Exception as erro:
        st.error(f'Não foi possível carregar os dados do dashboard: {erro}')
        return

    leads_ativos = [x for x in leads if _ativo(x)]
    orcamentos_ativos = [x for x in orcamentos if _ativo(x)]
    ids_leads_ativos = {_texto(x.get('id')) for x in leads_ativos}
    ids_orcamentos_ativos = {_texto(x.get('id')) for x in orcamentos_ativos}
    ids_leads_todos = {_texto(x.get('id')) for x in leads}
    ids_orcamentos_todos = {_texto(x.get('id')) for x in orcamentos}

    def historico_elegivel(item):
        if not _ativo(item):
            return False
        lead_id = _texto(item.get('lead_id'))
        orc_id = _texto(item.get('orcamento_id'))
        if lead_id and lead_id in ids_leads_todos and lead_id not in ids_leads_ativos:
            return False
        if orc_id and orc_id in ids_orcamentos_todos and orc_id not in ids_orcamentos_ativos:
            return False
        return True

    historico = [x for x in historico if historico_elegivel(x)]
    inicio, fim, periodo = _datas_periodo()
    st.caption(f'Período selecionado: {periodo}. Arquivados excluídos inclusive do histórico.')

    leads_periodo = [x for x in leads_ativos if _no_periodo(
        _data(x, ['created_at', 'data_criacao', 'data_cadastro']), inicio, fim)]
    orcamentos_periodo = [x for x in orcamentos_ativos if _no_periodo(
        _data(x, ['created_at', 'data_criacao']), inicio, fim)]
    apresentados = [x for x in historico if (
        _texto(x.get('status_comercial')) in STATUS_APRESENTADO or
        _data(x, ['data_apresentacao']) is not None
    ) and _no_periodo(_data(x, ['data_apresentacao']), inicio, fim)]
    fechados_periodo = [x for x in historico if
        _texto(x.get('status_comercial')) == STATUS_FECHADO and
        _no_periodo(_data(x, ['data_fechamento']), inicio, fim)]

    # A taxa de conversão por coorte evita misturar leads e contratos de meses distintos.
    coorte = [x for x in historico if _no_periodo(
        _data(x, ['data_criacao', 'created_at']), inicio, fim)]
    fechados_coorte = [x for x in coorte if _texto(x.get('status_comercial')) == STATUS_FECHADO]
    taxa = len(fechados_coorte) / len(coorte) * 100 if coorte else 0.0
    prazo = _calcular_prazo_medio(pd.DataFrame(fechados_periodo))

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric('Leads recebidos', len(leads_periodo))
    c2.metric('Orçamentos', len(orcamentos_periodo))
    c3.metric('Preços apresentados', len(apresentados))
    c4.metric('Contratos fechados', len(fechados_periodo))
    c5.metric('Conversão da coorte', f'{taxa:.1f}%')
    c6.metric('Prazo médio', f'{prazo:.1f} dias' if prazo is not None else 'N/D')
    st.caption('Leads e orçamentos: data de criação. Preços apresentados: data de apresentação. '
               'Fechamentos: data de fechamento. Conversão da coorte: contratos atualmente '
               'fechados ÷ oportunidades criadas no período; não representa apenas fechamentos '
               'ocorridos no período. Prazo médio: apresentação até fechamento.')

    sem_data_apresentacao = sum(1 for x in historico if
        _texto(x.get('status_comercial')) in STATUS_APRESENTADO and
        _data(x, ['data_apresentacao']) is None)
    sem_data_fechamento = sum(1 for x in historico if
        _texto(x.get('status_comercial')) == STATUS_FECHADO and
        _data(x, ['data_fechamento']) is None)
    if sem_data_apresentacao or sem_data_fechamento:
        st.warning(f'Dados históricos incompletos: {sem_data_apresentacao} oportunidade(s) '
                   f'sem data de apresentação e {sem_data_fechamento} fechamento(s) '
                   'sem data de fechamento. Não foram atribuídas datas fictícias.')

    st.divider()
    st.subheader('Movimentações comerciais no período')
    df_funil = pd.DataFrame({'Evento': ['Leads recebidos', 'Orçamentos criados',
                                         'Preços apresentados', 'Contratos fechados'],
                             'Quantidade': [len(leads_periodo), len(orcamentos_periodo),
                                            len(apresentados), len(fechados_periodo)]})
    st.bar_chart(df_funil.set_index('Evento'))
    st.caption('O gráfico apresenta eventos do período, não etapas cumulativas de um funil.')

    st.divider()
    st.subheader('Índices por setor / segmento')
    resumo = _montar_indicadores_segmento(pd.DataFrame(historico), inicio, fim)
    if resumo.empty:
        st.info('Não existem oportunidades com data de criação no período selecionado.')
        return
    st.markdown('#### Conversão por segmento — coorte de criação')
    st.bar_chart(resumo.set_index('Segmento')[['Taxa de conversão (%)']])
    st.markdown('#### Desempenho comercial por segmento')
    st.dataframe(resumo, use_container_width=True, hide_index=True,
                 column_config={
                     'Taxa de conversão (%)': st.column_config.NumberColumn(format='%.1f%%'),
                     'Prazo médio (dias)': st.column_config.NumberColumn(format='%.1f'),
                 })
    com_venda = resumo[resumo['Contratos fechados'] > 0]
    if not com_venda.empty:
        melhor = com_venda.iloc[0]
        st.success(f"Melhor conversão da coorte: {melhor['Segmento']} — "
                   f"{melhor['Taxa de conversão (%)']:.1f}% "
                   f"({int(melhor['Contratos fechados'])} contrato(s)).")
