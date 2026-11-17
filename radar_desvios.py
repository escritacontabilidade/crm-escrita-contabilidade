"""Radar de desvios operacionais × honorários. Somente leitura; não altera Supabase."""
import pandas as pd
import streamlit as st

METRICAS = {
    'processos': ('Processos', 10),
    'notas_fiscais': ('Notas fiscais', 30),
    'contabil': ('Lançamentos contábeis', 30),
    'entradas': ('Entradas', 20),
    'saidas': ('Saídas', 20),
    'folha_pagamento': ('Folha de pagamento (volume)', 10),
    'admissao': ('Admissões', 5),
    'rescisao': ('Rescisões', 5),
}


def calcular_radar(h, p, competencia, meses=3, limiar_honorarios=10.0):
    """Retorna alertas e diagnóstico. Exige histórico pareado em meses anteriores.

    h e p já devem estar agregados por competência/código do cliente.
    Não interpreta ausência de produção como zero.
    """
    meses_anteriores = sorted(set(h['competencia']) & set(p['competencia']))
    meses_anteriores = [x for x in meses_anteriores if x < competencia][-meses:]
    if not meses_anteriores:
        return pd.DataFrame(), 'Não há competências anteriores presentes nas duas bases para comparação.'
    h = h.copy()
    p = p.copy()
    h['codigo_cliente'] = h['codigo_cliente'].astype(str)
    p['codigo_cliente'] = p['codigo_cliente'].astype(str)
    base = h.merge(p, on=['competencia', 'codigo_cliente'], how='inner', suffixes=('', '_prod'))
    atual = base[base['competencia'] == competencia]
    historico = base[base['competencia'].isin(meses_anteriores)]
    linhas = []
    for _, row in atual.iterrows():
        codigo = row['codigo_cliente']
        ant = historico[historico['codigo_cliente'] == codigo]
        if len(ant) < len(meses_anteriores):
            continue  # série incompleta: não estimar média com lacunas
        honorario_atual = float(row['valor_recorrente'])
        honorario_base = float(ant['valor_recorrente'].mean())
        if honorario_base <= 0:
            continue
        variacao_h = (honorario_atual / honorario_base - 1) * 100
        for campo, (rotulo, piso) in METRICAS.items():
            base_val = float(ant[campo].mean())
            atual_val = float(row[campo])
            if base_val < piso or atual_val <= base_val:
                continue
            variacao_p = (atual_val / base_val - 1) * 100
            if variacao_h > limiar_honorarios or variacao_p < 15:
                continue
            gravidade = 'Crítico' if variacao_p >= 50 else 'Alto' if variacao_p >= 30 else 'Moderado'
            linhas.append({
                'Prioridade': gravidade,
                'Código': codigo,
                'Cliente': row['cliente'],
                'Indicador': rotulo,
                'Média histórica': round(base_val, 1),
                'Mês atual': round(atual_val, 1),
                'Variação produção (%)': round(variacao_p, 1),
                'Honorário médio (R$)': round(honorario_base, 2),
                'Honorário atual (R$)': round(honorario_atual, 2),
                'Variação honorário (%)': round(variacao_h, 1),
                'Justificativa': f'{rotulo}: +{variacao_p:.1f}% vs. média histórica; honorários recorrentes: {variacao_h:+.1f}%. Verificar escopo e esforço antes de propor reajuste.',
            })
    resultado = pd.DataFrame(linhas)
    if not resultado.empty:
        resultado['_ordem'] = resultado['Prioridade'].map({'Crítico': 0, 'Alto': 1, 'Moderado': 2})
        resultado = resultado.sort_values(['_ordem', 'Variação produção (%)'], ascending=[True, False]).drop(columns='_ordem')
    return resultado, f'Base histórica: {", ".join(str(x)[:7] for x in meses_anteriores)}. Exigidos todos os meses da base para cada cliente.'


def exibir_radar(h, p, competencia):
    st.markdown('### Radar de Desvios — Produção × Honorários')
    st.caption('Diagnóstico para revisão comercial, não cálculo automático de reajuste. Comparação de volumes operacionais com a média histórica e honorários recorrentes.')
    if p.empty:
        st.info('Não há dados de produção disponíveis para calcular desvios.')
        return
    a, b = st.columns(2)
    with a:
        meses = st.selectbox('Meses anteriores para comparação', [3, 2, 1, 6], key='radar_meses')
    with b:
        limiar = st.number_input('Crescimento máximo dos honorários para alertar (%)', 0.0, 100.0, 10.0, 1.0, key='radar_limiar')
    alertas, diagnostico = calcular_radar(h, p, competencia, meses, limiar)
    st.caption(diagnostico)
    if alertas.empty:
        st.info('Nenhum desvio elegível encontrado. Confira a disponibilidade de histórico e os limites utilizados; isso não comprova ausência de riscos.')
        return
    a, b, c, d = st.columns(4)
    a.metric('Clientes sinalizados', alertas['Código'].nunique())
    b.metric('Alertas críticos', int((alertas['Prioridade'] == 'Crítico').sum()))
    c.metric('Alertas altos', int((alertas['Prioridade'] == 'Alto').sum()))
    d.metric('Alertas moderados', int((alertas['Prioridade'] == 'Moderado').sum()))
    nivel = st.multiselect('Filtrar gravidade', ['Crítico', 'Alto', 'Moderado'], default=['Crítico', 'Alto', 'Moderado'], key='radar_nivel')
    pesquisa = st.text_input('Buscar cliente ou código', key='radar_busca')
    exibicao = alertas[alertas['Prioridade'].isin(nivel)].copy()
    if pesquisa.strip():
        exibicao = exibicao[exibicao['Cliente'].astype(str).str.contains(pesquisa.strip(), case=False, regex=False) | exibicao['Código'].astype(str).str.contains(pesquisa.strip(), case=False, regex=False)]
    st.dataframe(exibicao, use_container_width=True, hide_index=True)
    st.download_button('Exportar alertas CSV', exibicao.to_csv(index=False).encode('utf-8-sig'), file_name=f'radar_desvios_{str(competencia)[:7]}.csv', mime='text/csv', key='radar_exportar')
    st.caption('Alertas não representam cobrança insuficiente comprovada. Aumento de faturamento do cliente não é usado como medida direta de esforço. Séries incompletas são excluídas da classificação.')
