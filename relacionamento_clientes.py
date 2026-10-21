"""Gestão de relacionamento da Escrita: cadastro, tratativas e follow-ups."""
from datetime import datetime, date, timedelta
import html
import streamlit as st

ETAPAS = {
    'Em aberto': 2,
    'Preço apresentado': 3,
    'Sem resposta': 5,
    'Contrato fechado': 15,
}
TIPOS = ['WhatsApp', 'Ligação', 'Reunião', 'E-mail', 'Visita', 'Observação', 'Outro']
SITUACOES = ['Prospect', 'Em negociação', 'Cliente contratado', 'Inativo']


def _rows(sb, tabela, campos='*'):
    return sb.table(tabela).select(campos).execute().data or []


def _txt(x):
    return str(x or '').strip()


def _dia(x):
    try:
        return datetime.fromisoformat(str(x).replace('Z', '+00:00')).date()
    except (ValueError, TypeError):
        return None


def _formatar(x):
    d = _dia(x)
    return d.strftime('%d/%m/%Y') if d else '—'


def _sincronizar_lead(sb, lead, existentes):
    """Cria o cadastro apenas mediante ação explícita do operador."""
    lid = int(lead['id'])
    if lid in existentes:
        return existentes[lid]
    nome = _txt(lead.get('nome_empresa'))
    if not nome:
        raise ValueError('O lead não possui nome da empresa.')
    payload = {
        'lead_id': lid, 'nome_empresa': nome,
        'cnpj': lead.get('cnpj'), 'segmento': lead.get('segmento'),
        'regime': lead.get('regime'), 'responsavel': lead.get('responsavel'),
        'telefone': lead.get('telefone'), 'whatsapp': lead.get('whatsapp'),
        'email': lead.get('email'), 'cidade': lead.get('cidade'),
        'uf': lead.get('uf'), 'situacao': 'Prospect', 'ativo': True,
    }
    retorno = sb.table('clientes').insert(payload).execute().data or []
    if not retorno:
        raise RuntimeError('O Supabase não retornou o cadastro criado.')
    return retorno[0]


def _formulario_cliente(sb, cliente=None):
    editando = cliente is not None
    cliente = cliente or {}
    ident = str(cliente.get('id', 'novo'))
    with st.form(f'crm_rel_cliente_form_{ident}'):
        st.markdown('**Dados cadastrais**')
        a, b = st.columns(2)
        with a:
            nome = st.text_input('Empresa *', value=_txt(cliente.get('nome_empresa')))
            cnpj = st.text_input('CNPJ', value=_txt(cliente.get('cnpj')))
            segmento = st.text_input('Segmento', value=_txt(cliente.get('segmento')))
            responsavel = st.text_input('Responsável', value=_txt(cliente.get('responsavel')))
            telefone = st.text_input('Telefone', value=_txt(cliente.get('telefone')))
            cidade = st.text_input('Cidade', value=_txt(cliente.get('cidade')))
        with b:
            situacao = st.selectbox('Situação', SITUACOES, index=SITUACOES.index(cliente.get('situacao')) if cliente.get('situacao') in SITUACOES else 0)
            regime = st.text_input('Regime', value=_txt(cliente.get('regime')))
            email = st.text_input('E-mail', value=_txt(cliente.get('email')))
            whatsapp = st.text_input('WhatsApp', value=_txt(cliente.get('whatsapp')))
            uf = st.text_input('UF', value=_txt(cliente.get('uf')))
            observacoes = st.text_area('Observações cadastrais', value=_txt(cliente.get('observacoes')))
        salvar = st.form_submit_button('Salvar cadastro', type='primary')
    if salvar:
        if not nome.strip():
            st.error('Informe o nome da empresa.')
            return
        payload = dict(nome_empresa=nome.strip(), cnpj=cnpj.strip() or None,
                       segmento=segmento.strip() or None, regime=regime.strip() or None,
                       responsavel=responsavel.strip() or None, telefone=telefone.strip() or None,
                       whatsapp=whatsapp.strip() or None, email=email.strip() or None,
                       cidade=cidade.strip() or None, uf=uf.strip() or None,
                       situacao=situacao, observacoes=observacoes.strip() or None,
                       updated_at=datetime.now().astimezone().isoformat())
        try:
            if editando:
                sb.table('clientes').update(payload).eq('id', cliente['id']).execute()
            else:
                payload['ativo'] = True
                sb.table('clientes').insert(payload).execute()
            st.success('Cadastro salvo.')
            st.rerun()
        except Exception as e:
            st.error(f'Erro ao salvar cadastro: {e}')


def _detalhes(sb, cliente, interacoes, followups, oportunidades):
    cid = int(cliente['id'])
    st.markdown(f"### {html.escape(_txt(cliente.get('nome_empresa')))}")
    st.caption(f"{_txt(cliente.get('situacao'))} · {_txt(cliente.get('segmento')) or 'Segmento não informado'} · {_txt(cliente.get('responsavel')) or 'Sem responsável'}")
    opcs = [o for o in oportunidades if (cliente.get('lead_id') is not None and str(o.get('lead_id')) == str(cliente['lead_id']))]
    if opcs:
        st.markdown('**Oportunidades vinculadas ao lead**')
        for o in opcs:
            st.caption(f"#{o.get('id')} · {_txt(o.get('status_comercial'))} · Orçamento #{o.get('orcamento_id') or '—'}")
    t1, t2, t3 = st.tabs(['Histórico de tratativas', 'Follow-ups', 'Editar cadastro'])
    with t1:
        registros = sorted([r for r in interacoes if r.get('cliente_id') == cid], key=lambda x: str(x.get('data_interacao') or ''), reverse=True)
        if not registros:
            st.info('Nenhuma tratativa registrada.')
        for r in registros:
            with st.container(border=True):
                st.markdown(f"**{html.escape(_txt(r.get('tipo')))}** · {_formatar(r.get('data_interacao'))} · {html.escape(_txt(r.get('responsavel')))}")
                st.write(_txt(r.get('descricao')))
        with st.form(f'rel_interacao_{cid}', clear_on_submit=True):
            st.markdown('**Registrar nova tratativa**')
            tipo = st.selectbox('Canal', TIPOS)
            responsavel = st.text_input('Responsável *', value=_txt(cliente.get('responsavel')))
            descricao = st.text_area('O que foi tratado? *')
            criar = st.form_submit_button('Registrar tratativa', type='primary')
        if criar:
            if not descricao.strip() or not responsavel.strip():
                st.warning('Informe responsável e descrição.')
            else:
                try:
                    sb.table('interacoes_clientes').insert({'cliente_id': cid, 'tipo': tipo, 'responsavel': responsavel.strip(), 'descricao': descricao.strip()}).execute()
                    st.success('Tratativa registrada.'); st.rerun()
                except Exception as e:
                    st.error(f'Erro ao registrar tratativa: {e}')
    with t2:
        tarefas = sorted([f for f in followups if f.get('cliente_id') == cid], key=lambda x: str(x.get('data_prevista') or ''))
        for f in tarefas:
            venc = _dia(f.get('data_prevista'))
            atrasado = f.get('status') == 'Pendente' and venc and venc < date.today()
            with st.container(border=True):
                st.write(f"**{_formatar(f.get('data_prevista'))}** · {f.get('status')}{' · ATRASADO' if atrasado else ''} · {_txt(f.get('responsavel'))}")
                st.write(_txt(f.get('descricao')))
                if f.get('status') == 'Pendente':
                    a, b = st.columns(2)
                    if a.button('Concluir', key=f'rel_concluir_{f["id"]}'):
                        try:
                            sb.table('followups_clientes').update({'status': 'Realizado', 'data_conclusao': datetime.now().astimezone().isoformat()}).eq('id', f['id']).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                    if b.button('Cancelar', key=f'rel_cancelar_{f["id"]}'):
                        try:
                            sb.table('followups_clientes').update({'status': 'Cancelado'}).eq('id', f['id']).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
        status = next((_txt(o.get('status_comercial')) for o in opcs), '')
        dias = ETAPAS.get(status)
        if dias is not None:
            st.info(f'Sugestão pela etapa “{status}”: próximo contato em {dias} dia(s) corridos. Ajuste a data conforme a tratativa.')
        elif status == 'Negativa':
            st.caption('Negativa: sem sugestão automática de follow-up.')
        with st.form(f'rel_followup_{cid}', clear_on_submit=True):
            st.markdown('**Agendar acompanhamento**')
            data = st.date_input('Data prevista', value=date.today() + timedelta(days=dias or 3))
            responsavel = st.text_input('Responsável *', value=_txt(cliente.get('responsavel')), key=f'rel_resp_fu_{cid}')
            descricao = st.text_area('Próxima ação *', placeholder='Ex.: retornar sobre a proposta enviada.')
            agendar = st.form_submit_button('Agendar follow-up', type='primary')
        if agendar:
            if not descricao.strip() or not responsavel.strip():
                st.warning('Informe responsável e próxima ação.')
            else:
                try:
                    sb.table('followups_clientes').insert({'cliente_id': cid, 'responsavel': responsavel.strip(), 'descricao': descricao.strip(), 'data_prevista': f'{data.isoformat()}T12:00:00-03:00', 'status': 'Pendente', 'origem_sugestao': 'Regra comercial' if dias else 'Manual'}).execute()
                    st.success('Follow-up agendado.'); st.rerun()
                except Exception as e:
                    st.error(f'Erro ao agendar: {e}')
    with t3:
        _formulario_cliente(sb, cliente)


def renderizar_relacionamento_clientes(sb, oportunidades=None):
    """Renderizado após o editor do Pipeline, sem afetar filtros ou métricas existentes."""
    st.divider()
    st.header('Relacionamento com clientes')
    st.caption('Cadastro centralizado, histórico de tratativas e agenda de follow-ups. Os filtros do Pipeline não restringem esta área.')
    try:
        clientes = [c for c in _rows(sb, 'clientes') if c.get('ativo') is not False]
        interacoes = _rows(sb, 'interacoes_clientes')
        followups = _rows(sb, 'followups_clientes')
        leads = [l for l in _rows(sb, 'leads_externos', 'id,nome_empresa,cnpj,segmento,regime,responsavel,telefone,whatsapp,email,cidade,uf,ativo') if l.get('ativo') is True]
    except Exception as e:
        st.error(f'Não foi possível carregar o relacionamento: {e}')
        st.info('Confira as tabelas e as permissões de acesso no Supabase.')
        return
    oportunidades = oportunidades if oportunidades is not None else []
    if hasattr(oportunidades, 'to_dict'):
        oportunidades = oportunidades.to_dict('records')
    hoje = date.today()
    pendentes = [f for f in followups if f.get('status') == 'Pendente' and any(c.get('id') == f.get('cliente_id') for c in clientes)]
    atrasados = [f for f in pendentes if _dia(f.get('data_prevista')) and _dia(f.get('data_prevista')) < hoje]
    hoje_lista = [f for f in pendentes if _dia(f.get('data_prevista')) == hoje]
    a, b, c, d = st.columns(4)
    a.metric('Clientes cadastrados', len(clientes))
    b.metric('Follow-ups pendentes', len(pendentes))
    c.metric('Atrasados', len(atrasados))
    d.metric('Para hoje', len(hoje_lista))
    with st.expander('Cadastrar novo cliente ou prospect'):
        _formulario_cliente(sb)
    vinculados = {int(c['lead_id']): c for c in clientes if c.get('lead_id') is not None}
    sem_cadastro = [l for l in leads if int(l['id']) not in vinculados]
    with st.expander(f'Vincular lead existente ao cadastro ({len(sem_cadastro)} disponíveis)'):
        st.caption('O vínculo é individual e não converte o lead automaticamente em cliente contratado.')
        if sem_cadastro:
            mapa = {f"#{l['id']} · {_txt(l.get('nome_empresa'))}": l for l in sem_cadastro}
            escolha = st.selectbox('Lead', list(mapa), key='rel_lead_vincular')
            if st.button('Criar cadastro vinculado', key='rel_criar_vinculo'):
                try:
                    _sincronizar_lead(sb, mapa[escolha], vinculados)
                    st.success('Cadastro criado e vinculado.'); st.rerun()
                except Exception as e:
                    st.error(f'Não foi possível vincular: {e}')
        else:
            st.caption('Todos os leads ativos já possuem cadastro vinculado.')
    busca = st.text_input('Pesquisar cliente', placeholder='Empresa, CNPJ ou responsável', key='rel_busca')
    filtro = st.selectbox('Situação do relacionamento', ['Todas'] + SITUACOES, key='rel_situacao')
    encontrados = [c for c in clientes if (filtro == 'Todas' or c.get('situacao') == filtro) and (not busca or busca.lower() in ' '.join(_txt(c.get(k)) for k in ('nome_empresa', 'cnpj', 'responsavel')).lower())]
    if not encontrados:
        st.info('Nenhum cliente cadastrado para os filtros selecionados. Cadastre um cliente ou vincule um lead acima.')
        return
    st.markdown('### Cards de relacionamento')
    selecionados = {}
    for i in range(0, len(encontrados), 3):
        cols = st.columns(3)
        for col, cliente in zip(cols, encontrados[i:i+3]):
            cid = int(cliente['id'])
            regs = [r for r in interacoes if r.get('cliente_id') == cid]
            ultima = max((r.get('data_interacao') for r in regs if r.get('data_interacao')), default=None)
            tarefas = [f for f in pendentes if f.get('cliente_id') == cid]
            proximo = min((f.get('data_prevista') for f in tarefas if f.get('data_prevista')), default=None)
            atrasado = any(_dia(f.get('data_prevista')) and _dia(f.get('data_prevista')) < hoje for f in tarefas)
            with col:
                with st.container(border=True):
                    st.markdown(f"**{html.escape(_txt(cliente.get('nome_empresa')))}**")
                    st.caption(f"{_txt(cliente.get('situacao'))} · {_txt(cliente.get('segmento')) or 'Sem segmento'}")
                    st.write(f"Responsável: {_txt(cliente.get('responsavel')) or '—'}")
                    st.write(f"Última tratativa: {_formatar(ultima)}")
                    st.write(f"Próximo follow-up: {_formatar(proximo)}{' · ATRASADO' if atrasado else ''}")
                    if st.button('Abrir histórico', key=f'rel_abrir_{cid}', use_container_width=True):
                        st.session_state['rel_cliente_selecionado'] = cid
    selecionado = st.session_state.get('rel_cliente_selecionado')
    cliente = next((c for c in clientes if c.get('id') == selecionado), None)
    if cliente:
        st.divider()
        _detalhes(sb, cliente, interacoes, followups, oportunidades)
