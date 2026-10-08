"""Honorários do CRM Escrita: leitura admin/comercial, alteração somente admin."""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pandas as pd
import streamlit as st
from database_admin import exigir_admin, exigir_acesso_honorarios, get_supabase_admin, get_supabase_financeiro

CAMPOS_VALORES = {
    'Vl. Recorrente': 'valor_recorrente',
    'Vl. Variável': 'valor_variavel',
    'Vl. Adicional Anual': 'valor_adicional_anual',
    'Vl. Contrato': 'valor_total',
}
MESES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']


def moeda(v):
    return 'R$ ' + f'{float(v):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def normalizar_codigo(v):
    texto = str(v).strip()
    return str(int(texto)) if re.fullmatch(r'\d+', texto) else texto


def ler_honorarios(arquivo):
    """Lê cabeçalho dinâmico e descarta subtotais e rodapé."""
    arquivo.seek(0)
    bruto = pd.read_excel(arquivo, sheet_name=0, header=None)
    indice = None
    for i, linha in bruto.iterrows():
        valores = [str(v).strip() for v in linha.tolist()]
        if 'Cliente' in valores and 'Vl. Recorrente' in valores and 'Nr. Documento' in valores:
            indice = i
            break
    if indice is None:
        raise ValueError('Cabeçalho do relatório não encontrado (Cliente / Vl. Recorrente / Nr. Documento).')
    arquivo.seek(0)
    df = pd.read_excel(arquivo, sheet_name=0, header=indice)
    df.columns = [str(c).strip() for c in df.columns]
    obrigatorias = ['Estabelecimento','Data Emissão','Nr. Documento','Cliente', *CAMPOS_VALORES.keys()]
    faltantes = [c for c in obrigatorias if c not in df.columns]
    if faltantes:
        raise ValueError('Colunas ausentes: ' + ', '.join(faltantes))
    # Apenas documentos identificados, sem linhas de totais por estabelecimento.
    df = df[df['Estabelecimento'].notna() & df['Nr. Documento'].notna()].copy()
    partes = df['Cliente'].astype(str).str.extract(r'^\s*(\d+)\s+-\s+(.+?)\s*$')
    invalidos = partes[0].isna()
    if invalidos.any():
        raise ValueError(f'{invalidos.sum()} documento(s) com código de cliente inválido; importação bloqueada.')
    df['codigo_cliente'] = partes[0].map(normalizar_codigo)
    df['cliente_nome'] = partes[1].str.strip()
    for origem, destino in CAMPOS_VALORES.items():
        df[destino] = pd.to_numeric(df[origem], errors='coerce')
        if df[destino].isna().any():
            raise ValueError(f'Valores inválidos na coluna {origem}.')
        df[destino] = df[destino].round(2)
    diferenca = (df['valor_recorrente'] + df['valor_variavel'] + df['valor_adicional_anual'] - df['valor_total']).abs()
    if (diferenca > .011).any():
        raise ValueError(f'{(diferenca > .011).sum()} documento(s) não conciliam com Vl. Contrato.')
    datas = pd.to_datetime(df['Data Emissão'], errors='coerce')
    if datas.isna().any():
        raise ValueError('Há documentos sem data de emissão válida.')
    df['data_emissao_iso'] = datas.dt.strftime('%Y-%m-%d')
    df['numero_documento'] = df['Nr. Documento'].map(lambda v: str(int(v)) if isinstance(v, (float, int)) and float(v).is_integer() else str(v).strip())
    return df.reset_index(drop=True)


def paginar(tabela, campos, **filtros):
    exigir_acesso_honorarios()
    db = get_supabase_financeiro()
    saida = []
    offset = 0
    while True:
        consulta = db.table(tabela).select(campos)
        for coluna, valor in filtros.items():
            consulta = consulta.eq(coluna, valor)
        lote = consulta.order('id').range(offset, offset + 999).execute().data or []
        saida.extend(lote)
        if len(lote) < 1000:
            break
        offset += 1000
    return saida


def registros_importacao(df, competencia, arquivo):
    registros = []
    for _, r in df.iterrows():
        registros.append({
            'competencia': competencia,
            'codigo_cliente': r['codigo_cliente'],
            'cliente': r['cliente_nome'],
            'estabelecimento': str(r['Estabelecimento']).strip(),
            'numero_documento': r['numero_documento'],
            'data_emissao': r['data_emissao_iso'],
            **{dest: str(Decimal(str(r[dest])).quantize(Decimal('0.01'))) for dest in CAMPOS_VALORES.values()},
            'arquivo_origem': arquivo,
        })
    return registros


def gravar_lotes(db, registros):
    for inicio in range(0, len(registros), 100):
        db.table('honorarios_clientes').insert(registros[inicio:inicio+100]).execute()


def tela_consulta_honorarios():
    """Consulta financeira sem recursos de importação, exclusão ou substituição."""
    exigir_acesso_honorarios()
    st.subheader('Honorários — consulta')
    st.caption('Consulta de honorários recorrentes, variáveis e adicionais anuais. Alterações são exclusivas do administrador.')
    try:
        registros = paginar('honorarios_clientes', 'id,competencia,codigo_cliente,cliente,estabelecimento,numero_documento,valor_recorrente,valor_variavel,valor_adicional_anual,valor_total')
    except Exception as exc:
        st.error(f'Não foi possível consultar os honorários: {exc}')
        return
    if not registros:
        st.info('Ainda não existem honorários importados.')
        return
    df = pd.DataFrame(registros)
    for c in ['valor_recorrente','valor_variavel','valor_adicional_anual','valor_total']:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    opcoes = sorted(df['competencia'].dropna().unique().tolist(), reverse=True)
    competencia = st.selectbox('Competência', opcoes, key='hon_consulta_comp')
    atual = df[df['competencia'] == competencia].copy()
    resumo = atual.groupby(['codigo_cliente','cliente'], as_index=False)[['valor_recorrente','valor_variavel','valor_adicional_anual','valor_total']].sum()
    c1,c2,c3,c4 = st.columns(4)
    c1.metric('Clientes', resumo['codigo_cliente'].nunique())
    c2.metric('Honorários recorrentes', moeda(resumo['valor_recorrente'].sum()))
    c3.metric('Receitas variáveis', moeda(resumo['valor_variavel'].sum()))
    c4.metric('Receita total', moeda(resumo['valor_total'].sum()))
    st.dataframe(resumo.sort_values('cliente'), use_container_width=True, hide_index=True)
    st.caption(f'{len(atual)} documento(s) na competência. Adicional anual: {moeda(resumo["valor_adicional_anual"].sum())}.')


def tela_honorarios():
    exigir_admin()
    st.subheader('Honorários — importação e conferência')
    st.caption('Receita recorrente, variável e adicional anual permanecem separados. Importação exclusiva do administrador.')
    db = get_supabase_admin()
    col1, col2 = st.columns(2)
    with col1:
        mes = st.selectbox('Mês da competência', MESES, index=datetime.now().month-1, key='hon_mes')
    with col2:
        ano = st.number_input('Ano da competência', min_value=2020, max_value=2100, value=datetime.now().year, step=1, key='hon_ano')
    competencia = f'{int(ano)}-{MESES.index(mes)+1:02d}-01'
    arquivo = st.file_uploader('Relatório Contratos Faturados Sintético (.xlsx)', type=['xlsx'], key='hon_arquivo')
    if arquivo is None:
        st.info('Selecione um relatório para validar os documentos antes de gravar.')
        return
    try:
        df = ler_honorarios(arquivo)
        if df.empty:
            st.error('Nenhum documento válido encontrado.')
            return
        meses_emissao = pd.to_datetime(df['data_emissao_iso']).dt.strftime('%Y-%m').unique().tolist()
        mes_selecionado = competencia[:7]
        if meses_emissao != [mes_selecionado]:
            st.error(f'Datas de emissão encontradas: {", ".join(meses_emissao)}. Competência selecionada: {mes_selecionado}. Corrija antes de importar.')
            return
        c1,c2,c3,c4 = st.columns(4)
        c1.metric('Documentos', len(df))
        c2.metric('Clientes únicos', df['codigo_cliente'].nunique())
        c3.metric('Honorários recorrentes', moeda(df['valor_recorrente'].sum()))
        c4.metric('Receita total', moeda(df['valor_total'].sum()))
        st.write('Variáveis:', moeda(df['valor_variavel'].sum()), ' | Adicional anual:', moeda(df['valor_adicional_anual'].sum()))
        st.dataframe(df[['Estabelecimento','codigo_cliente','cliente_nome','numero_documento','valor_recorrente','valor_variavel','valor_adicional_anual','valor_total']], use_container_width=True, hide_index=True)
        existentes = paginar('honorarios_clientes', 'id,competencia,codigo_cliente,cliente,estabelecimento,numero_documento,data_emissao,valor_recorrente,valor_variavel,valor_adicional_anual,valor_total,arquivo_origem', competencia=competencia)
        st.write(f'Registros existentes em {mes}/{ano}: **{len(existentes)}**')
        confirmar = st.checkbox('Confirmo os totais e a competência informada.', key='hon_confirma')
        if existentes:
            st.warning('Substituição de competência existente: a operação envolve exclusão e reinserção e não é transacional. Faça backup antes de prosseguir.')
            st.download_button('Baixar backup da competência atual (CSV)', pd.DataFrame(existentes).to_csv(index=False).encode('utf-8-sig'), file_name=f'backup_honorarios_{competencia}.csv', mime='text/csv')
            confirmar_substituicao = st.checkbox('Baixei o backup e autorizo substituir todos os documentos deste mês.', key='hon_substituir')
        else:
            confirmar_substituicao = True
        if st.button('Importar honorários' if not existentes else 'Substituir honorários da competência', type='primary', disabled=not (confirmar and confirmar_substituicao), key='hon_gravar'):
            exigir_admin()  # Revalidação no momento da gravação.
            registros = registros_importacao(df, competencia, arquivo.name)
            try:
                if existentes:
                    db.table('honorarios_clientes').delete().eq('competencia', competencia).execute()
                gravar_lotes(db, registros)
                gravados = paginar('honorarios_clientes', 'id', competencia=competencia)
                if len(gravados) != len(registros):
                    raise RuntimeError(f'Conferência falhou: esperados {len(registros)}, encontrados {len(gravados)}.')
                st.success(f'{len(registros)} documentos importados e conferidos para {mes}/{ano}.')
            except Exception:
                st.error('Falha na gravação. A competência pode estar parcialmente gravada; utilize o backup e NÃO faça nova importação antes de conferir o banco.')
                raise
    except Exception as exc:
        st.error(f'Não foi possível validar ou consultar o relatório: {exc}')


def tela_cruzamento():
    exigir_acesso_honorarios()
    st.subheader('Produção × Honorários')
    st.caption('O faturamento da produção representa a movimentação do cliente; não é receita de honorários da Escrita.')
    try:
        honorarios = paginar('honorarios_clientes', 'id,competencia,codigo_cliente,cliente,valor_recorrente,valor_variavel,valor_adicional_anual,valor_total')
        producao = paginar('producao_clientes', 'id,competencia,codigo_cliente,cliente,sistema,folha_pagamento,admissao,rescisao,contabil,entradas,saidas,notas_fiscais,processos,faturamento')
    except Exception as exc:
        st.error(f'Erro ao consultar dados: {exc}')
        return
    if not honorarios:
        st.info('Importe os honorários para habilitar o comparativo.')
        return
    h = pd.DataFrame(honorarios)
    h['codigo_cliente'] = h['codigo_cliente'].map(normalizar_codigo)
    valores = ['valor_recorrente','valor_variavel','valor_adicional_anual','valor_total']
    for c in valores:
        h[c] = pd.to_numeric(h[c], errors='coerce').fillna(0)
    h = h.groupby(['competencia','codigo_cliente'], as_index=False).agg(cliente=('cliente','first'), **{c:(c,'sum') for c in valores})
    if producao:
        p = pd.DataFrame(producao)
        p['codigo_cliente'] = p['codigo_cliente'].map(normalizar_codigo)
        metricas = ['folha_pagamento','admissao','rescisao','contabil','entradas','saidas','notas_fiscais','processos','faturamento']
        for c in metricas:
            p[c] = pd.to_numeric(p[c], errors='coerce').fillna(0)
        p = p.groupby(['competencia','codigo_cliente'], as_index=False)[metricas].sum()
        unido = h.merge(p, on=['competencia','codigo_cliente'], how='left', indicator=True)
        unido['Situação'] = unido['_merge'].map({'left_only':'Sem produção correspondente','both':'Conciliado','right_only':'Sem honorários'}).astype(str)
        unido = unido.drop(columns=['_merge'])
    else:
        unido = h.copy()
        unido['Situação'] = 'Sem produção correspondente'
    opcoes = sorted(unido['competencia'].dropna().unique().tolist(), reverse=True)
    escolha = st.selectbox('Competência', opcoes, key='hon_cruz_comp')
    atual = unido[unido['competencia'] == escolha].copy()
    c1,c2,c3 = st.columns(3)
    c1.metric('Clientes com honorários', atual['codigo_cliente'].nunique())
    c2.metric('Honorários recorrentes', moeda(atual['valor_recorrente'].sum()))
    c3.metric('Receita total', moeda(atual['valor_total'].sum()))
    faltantes = atual[atual['Situação'] != 'Conciliado']
    if not faltantes.empty:
        st.warning(f'{len(faltantes)} cliente(s) com honorários sem produção correspondente neste mês. Verifique códigos e importações.')
    st.dataframe(atual.drop(columns=['competencia']).sort_values('cliente'), use_container_width=True, hide_index=True)
    st.download_button('Exportar comparativo CSV', atual.to_csv(index=False).encode('utf-8-sig'), file_name=f'producao_honorarios_{escolha}.csv', mime='text/csv')
    historico = h.sort_values('competencia').copy()
    historico['recorrente_anterior'] = historico.groupby('codigo_cliente')['valor_recorrente'].shift(1)
    historico['variacao_honorario_pct'] = ((historico['valor_recorrente'] / historico['recorrente_anterior']) - 1) * 100
    historico.loc[historico['recorrente_anterior'].isna() | (historico['recorrente_anterior'] == 0), 'variacao_honorario_pct'] = float('nan')
    st.markdown('#### Evolução do honorário recorrente')
    st.caption('A variação compara com a competência anterior disponível do cliente. Não é uma sugestão automática de reajuste.')
    st.dataframe(historico[historico['competencia'] == escolha][['codigo_cliente','cliente','valor_recorrente','recorrente_anterior','variacao_honorario_pct']].sort_values('cliente'), use_container_width=True, hide_index=True)
