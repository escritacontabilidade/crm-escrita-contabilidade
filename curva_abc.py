"""Curva ABC de honorários; configuração compartilhada, sem alterar faturamento."""
from io import BytesIO
from datetime import datetime, timezone
from decimal import Decimal
import pandas as pd
import streamlit as st
import altair as alt
from database_admin import exigir_acesso_honorarios, get_supabase_financeiro, get_supabase_admin
from monitoramento_honorarios import paginar, moeda, normalizar_codigo
from regime_tributario import REGIMES, consolidar_regime, normalizar_regime

GRUPOS = ['A', 'B', 'C']
PADRAO = [20, 30, 50]

def classificar(df, metas):
    if len(metas) != 3 or any(x < 0 or x > 100 for x in metas) or sum(Decimal(str(x)) for x in metas) != 100:
        raise ValueError('Os percentuais devem somar 100%.')
    d = df.sort_values(['Honorários', 'Código'], ascending=[False, True]).reset_index(drop=True).copy()
    if (d['Honorários'] < 0).any():
        raise ValueError('Há clientes com saldo negativo. Selecione outra base ou período para calcular uma curva acumulada válida.')
    total = d['Honorários'].sum()
    if total <= 0:
        raise ValueError('Não há honorários positivos no recorte.')
    d['% total'] = d['Honorários'] / total * 100
    d['% acumulado'] = d['% total'].cumsum()
    limites = [sum(metas[:i+1]) for i in range(3)]
    def grupo(anterior, valor):
        if valor == 0:
            return next(g for g, m in reversed(list(zip(GRUPOS, metas))) if m > 0)
        return next((g for g,m,l in zip(GRUPOS,metas,limites) if m > 0 and anterior < l - 1e-9), next(g for g,m in reversed(list(zip(GRUPOS,metas))) if m > 0))
    d['Grupo'] = [grupo(a-p,v) for a,p,v in zip(d['% acumulado'],d['% total'],d['Honorários'])]
    soma = d.groupby('Grupo')['Honorários'].transform('sum')
    d['% grupo'] = d['Honorários'].div(soma.where(soma != 0)).fillna(0)*100
    d['Posição'] = d.index + 1
    return d

def tela_curva_abc():
    exigir_acesso_honorarios()
    st.subheader('Curva ABC de Clientes')
    st.caption('Classificação por participação nos honorários, do maior para o menor cliente.')
    try:
        db = get_supabase_financeiro()
        cfg = db.table('configuracao_curva_abc').select('percentual_a,percentual_b,percentual_c').eq('id',1).execute().data
        if not cfg:
            raise ValueError('Configuração ABC não encontrada.')
        metas = [float(cfg[0]['percentual_'+g.lower()]) for g in GRUPOS]
        h = pd.DataFrame(paginar('honorarios_clientes','id,competencia,codigo_cliente,cliente,valor_recorrente,valor_total'))
    except Exception as e:
        st.error(f'Não foi possível carregar a Curva ABC: {e}')
        return
    admin = st.session_state.get('perfil_usuario') == 'admin'
    with st.expander('Configuração dos grupos'):
        tabela = pd.DataFrame({'Grupo':GRUPOS,'Percentual (%)':metas})
        edit = st.data_editor(tabela, hide_index=True, disabled=['Grupo'] if admin else True, key='abc_config_'+str(metas), column_config={'Percentual (%)':st.column_config.NumberColumn(min_value=0,max_value=100,step=0.01,format='%.2f')})
        novos = edit['Percentual (%)'].tolist()
        valido = all(pd.notna(x) and 0 <= x <= 100 for x in novos) and sum(Decimal(str(x)) for x in novos)==100
        st.write(f'Total: {sum(novos):.2f}%')
        if not valido: st.warning('A soma deve ser exatamente 100%.')
        if admin:
            c1,c2 = st.columns(2)
            salvar = c1.button('Salvar percentuais',disabled=not valido,key='abc_salvar')
            restaurar = c2.button('Restaurar 20 / 30 / 50',key='abc_restaurar')
            if salvar or restaurar:
                valores = PADRAO if restaurar else novos
                try:
                    get_supabase_admin().table('configuracao_curva_abc').update({**{'percentual_'+g.lower():float(v) for g,v in zip(GRUPOS,valores)},'updated_at':datetime.now(timezone.utc).isoformat()}).eq('id',1).execute()
                    st.rerun()
                except Exception as e: st.error(f'Erro ao salvar: {e}')
    if h.empty:
        st.info('Importe honorários para consultar a curva.'); return
    meses = sorted(h['competencia'].dropna().unique())
    modo = st.radio('Período',['Mensal','Intervalo'],horizontal=True,key='abc_periodo')
    if modo == 'Mensal':
        inicio = fim = st.selectbox('Competência',meses,index=len(meses)-1,key='abc_mes')
    else:
        c1,c2=st.columns(2)
        inicio=c1.selectbox('De',meses,key='abc_inicio'); fim=c2.selectbox('Até',meses,index=len(meses)-1,key='abc_fim')
    if inicio > fim: st.warning('Período inválido.'); return
    base=st.radio('Base de cálculo',['Recorrentes','Totais'],horizontal=True,key='abc_base')
    campo='valor_recorrente' if base=='Recorrentes' else 'valor_total'
    h=h[h['competencia'].between(inicio,fim)].copy()
    h['codigo_cliente']=h['codigo_cliente'].map(normalizar_codigo)
    h[campo]=pd.to_numeric(h[campo],errors='coerce')
    if h[campo].isna().any(): st.error('Honorários inválidos no período.'); return
    try:
        p=pd.DataFrame(paginar('producao_clientes','id,competencia,codigo_cliente,regime_tributario',competencia=fim))
    except Exception as e:
        st.error(f'Erro ao consultar regimes: {e}'); return
    regimes={}
    if not p.empty:
        p['codigo_cliente']=p['codigo_cliente'].map(normalizar_codigo)
        regimes=p.groupby('codigo_cliente')['regime_tributario'].agg(consolidar_regime).to_dict()
    d=h.sort_values('competencia').groupby('codigo_cliente',as_index=False).agg(Cliente=('cliente','last'),Honorarios=(campo,'sum')).rename(columns={'codigo_cliente':'Código','Honorarios':'Honorários'})
    d['Regime tributário']=d['Código'].map(regimes).map(normalizar_regime)
    selecionados=st.multiselect('Regime tributário',REGIMES,default=REGIMES,key='abc_regimes',help='Classificação na última competência selecionada; sem imputação histórica.')
    d=d[d['Regime tributário'].isin(selecionados)]
    try: d=classificar(d,metas)
    except ValueError as e: st.warning(str(e)); return
    total=d['Honorários'].sum()
    resumo=[]
    for g,m in zip(GRUPOS,metas):
        s=d[d['Grupo']==g]['Honorários']; v=s.sum()
        resumo.append({'Grupo':g,'Meta (%)':m,'Real (%)':v/total*100,'Clientes':len(s),'% clientes':len(s)/len(d)*100,'Honorários':v,'Ticket médio':s.mean() if len(s) else 0,'Maior':s.max() if len(s) else 0,'Menor':s.min() if len(s) else 0})
    r=pd.DataFrame(resumo)
    cols=st.columns(4); cols[0].metric('Honorários',moeda(total))
    for c,row in zip(cols[1:],resumo): c.metric('Grupo '+row['Grupo'],f"{row['Real (%)']:.2f}%",f"{row['Clientes']} clientes",delta_color='off')
    st.caption('O cliente que ultrapassa um limite permanece no grupo que estava sendo preenchido. A participação real pode diferir da meta. Percentuais calculados sobre o universo filtrado.')
    st.dataframe(r,hide_index=True,use_container_width=True)
    st.bar_chart(r.set_index('Grupo')[['Meta (%)','Real (%)']])
    barras=alt.Chart(d).mark_bar().encode(x=alt.X('Posição:Q',title='Clientes em ordem decrescente'),y=alt.Y('Honorários:Q'),color='Grupo:N',tooltip=['Cliente','Honorários','% total','Grupo'])
    linha=alt.Chart(d).mark_line(color='#b45309').encode(x='Posição:Q',y=alt.Y('% acumulado:Q',scale=alt.Scale(domain=[0,100])),tooltip=['Cliente','% acumulado'])
    st.altair_chart(alt.layer(barras,linha).resolve_scale(y='independent'),use_container_width=True)
    grupos=st.multiselect('Grupos para detalhar',GRUPOS,default=GRUPOS,key='abc_grupos')
    busca=st.text_input('Buscar cliente ou código',key='abc_busca').strip()
    detalhe=d[d['Grupo'].isin(grupos)]
    if busca: detalhe=detalhe[detalhe['Cliente'].astype(str).str.contains(busca,case=False,regex=False)|detalhe['Código'].str.contains(busca,regex=False)]
    for g in grupos:
        with st.expander(f'Grupo {g} — {len(detalhe[detalhe.Grupo==g])} clientes exibidos'):
            st.dataframe(detalhe[detalhe.Grupo==g],hide_index=True,use_container_width=True,column_config={c:st.column_config.NumberColumn(format='%.2f %%') for c in ['% total','% grupo','% acumulado']})
    out=BytesIO()
    with pd.ExcelWriter(out,engine='openpyxl') as writer:
        r.to_excel(writer,sheet_name='Resumo',index=False)
        d.to_excel(writer,sheet_name='Carteira classificada',index=False)
        for g in GRUPOS: detalhe[detalhe.Grupo==g].to_excel(writer,sheet_name='Grupo '+g,index=False)
    st.download_button('Exportar Curva ABC para Excel',out.getvalue(),file_name='curva_abc.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key='abc_exportar')
