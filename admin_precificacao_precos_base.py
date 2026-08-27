import pandas as pd
import streamlit as st


def limpar_cache_precos_base():
    st.cache_data.clear()


def carregar_precos_base(supabase):
    resposta = (
        supabase
        .table("precos_base_precificacao")
        .select("*")
        .order("tabela_base")
        .order("regime")
        .order("faixa_inicial")
        .execute()
    )
    return resposta.data or []


def carregar_mapa_segmentos(supabase):
    try:
        resposta = (
            supabase
            .table("mapa_segmento_precificacao")
            .select("*")
            .eq("ativo", True)
            .order("segmento_questionario")
            .execute()
        )
        return resposta.data or []
    except Exception:
        return []


def montar_mapa_tabela_para_segmentos(registros):
    mapa = {}
    for registro in registros:
        tabela_base = str(registro.get("tabela_base") or "").strip()
        segmento = str(registro.get("segmento_questionario") or "").strip()
        if not tabela_base or not segmento:
            continue
        mapa.setdefault(tabela_base, [])
        if segmento not in mapa[tabela_base]:
            mapa[tabela_base].append(segmento)
    return mapa


def formatar_faixa_preco(registro):
    inicio = float(registro.get("faixa_inicial") or 0)
    if bool(registro.get("sem_limite_superior")):
        return f"A partir de {inicio:,.2f}"
    final = float(registro.get("faixa_final") or 0)
    return f"{inicio:,.2f} até {final:,.2f}"


def validar_preco_base(
    tabela_base,
    regime,
    faixa_inicial,
    faixa_final,
    sem_limite_superior,
    valor_base,
    registros_existentes,
    registro_id_edicao=None,
):
    erros = []
    tabela_base = str(tabela_base or "").strip()
    regime = str(regime or "").strip()

    if not tabela_base:
        erros.append("Informe a tabela base.")
    if not regime:
        erros.append("Informe o regime tributário.")
    if faixa_inicial is None:
        erros.append("Informe a faixa inicial.")
    elif float(faixa_inicial) < 0:
        erros.append("A faixa inicial não pode ser negativa.")

    if not sem_limite_superior:
        if faixa_final is None:
            erros.append("Informe a faixa final.")
        elif float(faixa_final) < float(faixa_inicial or 0):
            erros.append("A faixa final não pode ser menor que a faixa inicial.")

    if valor_base is None:
        erros.append("Informe o valor base.")
    elif float(valor_base) < 0:
        erros.append("O valor base não pode ser negativo.")

    if erros:
        return erros

    novo_inicio = float(faixa_inicial)
    novo_final = float("inf") if sem_limite_superior else float(faixa_final)

    for registro in registros_existentes:
        if registro.get("ativo") is False:
            continue
        if registro_id_edicao is not None and int(registro.get("id")) == int(registro_id_edicao):
            continue

        mesma_tabela = str(registro.get("tabela_base") or "").strip() == tabela_base
        mesmo_regime = str(registro.get("regime") or "").strip() == regime
        if not (mesma_tabela and mesmo_regime):
            continue

        inicio_existente = float(registro.get("faixa_inicial") or 0)
        final_existente = (
            float("inf")
            if registro.get("sem_limite_superior")
            else float(registro.get("faixa_final") or 0)
        )

        if novo_inicio <= final_existente and novo_final >= inicio_existente:
            erros.append(
                "A faixa informada entra em conflito com outra faixa ativa "
                "da mesma tabela base e do mesmo regime."
            )
            break

    return erros


def renderizar_tabela_precos(registros, mapa_tabela_segmentos):
    linhas = []
    for registro in registros:
        tabela_base = str(registro.get("tabela_base") or "").strip()
        segmentos = mapa_tabela_segmentos.get(tabela_base, [])
        linhas.append({
            "ID": registro.get("id"),
            "Tabela base": tabela_base,
            "Segmentos": ", ".join(segmentos) if segmentos else "-",
            "Regime": registro.get("regime"),
            "Faixa": formatar_faixa_preco(registro),
            "Valor base": registro.get("valor_base"),
            "Ativo": "Sim" if registro.get("ativo") else "Não",
            "Observação": registro.get("observacao"),
        })

    if not linhas:
        st.info("Nenhum preço base encontrado.")
        return

    st.dataframe(
        pd.DataFrame(linhas),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Valor base": st.column_config.NumberColumn("Valor base", format="R$ %.2f"),
        },
    )


def renderizar_aba_precos_base(supabase):
    st.subheader("Preços Base")
    st.info(
        "Consulte, filtre, cadastre, edite, copie e inative os preços base usados na precificação."
    )

    try:
        registros = carregar_precos_base(supabase)
        mapa_segmentos = carregar_mapa_segmentos(supabase)
    except Exception as erro:
        st.error(f"Não foi possível carregar os preços base: {erro}")
        return

    mapa_tabela_segmentos = montar_mapa_tabela_para_segmentos(mapa_segmentos)

    st.markdown("### Consulta")
    tabelas_base = sorted({
        str(registro.get("tabela_base") or "").strip()
        for registro in registros
        if registro.get("tabela_base")
    })
    regimes = sorted({
        str(registro.get("regime") or "").strip()
        for registro in registros
        if registro.get("regime")
    })

    filtro1, filtro2, filtro3 = st.columns(3)
    with filtro1:
        pesquisa = st.text_input(
            "Pesquisar",
            placeholder="Tabela base, regime, segmento ou observação",
            key="admin_preco_pesquisa",
        )
    with filtro2:
        tabela_filtro = st.selectbox(
            "Tabela base",
            ["Todas"] + tabelas_base,
            key="admin_preco_tabela",
        )
    with filtro3:
        regime_filtro = st.selectbox(
            "Regime",
            ["Todos"] + regimes,
            key="admin_preco_regime",
        )

    mostrar_inativos = st.checkbox(
        "Mostrar registros inativos",
        value=False,
        key="admin_preco_inativos",
    )

    registros_filtrados = []
    termo = pesquisa.strip().lower()
    for registro in registros:
        ativo = bool(registro.get("ativo"))
        if not mostrar_inativos and not ativo:
            continue
        if tabela_filtro != "Todas" and registro.get("tabela_base") != tabela_filtro:
            continue
        if regime_filtro != "Todos" and registro.get("regime") != regime_filtro:
            continue

        tabela_base = str(registro.get("tabela_base") or "")
        segmentos = ", ".join(mapa_tabela_segmentos.get(tabela_base, []))
        texto_busca = " ".join([
            str(registro.get("id") or ""),
            tabela_base,
            str(registro.get("regime") or ""),
            segmentos,
            str(registro.get("observacao") or ""),
        ]).lower()
        if termo and termo not in texto_busca:
            continue
        registros_filtrados.append(registro)

    st.caption(f"{len(registros_filtrados)} registro(s) encontrado(s).")
    renderizar_tabela_precos(registros_filtrados, mapa_tabela_segmentos)

    st.download_button(
        "Exportar consulta para CSV",
        data=pd.DataFrame(registros_filtrados).to_csv(index=False).encode("utf-8-sig"),
        file_name="precos_base_precificacao.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.divider()
    aba_novo, aba_editar, aba_copiar = st.tabs([
        "➕ Novo preço base",
        "✏️ Editar ou inativar",
        "📋 Copiar preço base",
    ])

    with aba_novo:
        st.markdown("### Cadastrar novo preço base")
        with st.form("form_novo_preco_base"):
            tabela_base_nova = st.text_input("Tabela base", placeholder="Exemplo: Comercio")
            regime_novo = st.text_input("Regime tributário", placeholder="Exemplo: Simples")
            coluna1, coluna2 = st.columns(2)
            with coluna1:
                faixa_inicial_nova = st.number_input(
                    "Faixa inicial", min_value=0.0, step=0.01, format="%.2f"
                )
            with coluna2:
                sem_limite_novo = st.checkbox("Sem limite superior", value=False)
                faixa_final_nova = st.number_input(
                    "Faixa final",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    disabled=sem_limite_novo,
                )
            valor_base_novo = st.number_input(
                "Valor base (R$)", min_value=0.0, step=0.01, format="%.2f"
            )
            observacao_nova = st.text_area("Observação", height=80)
            salvar_novo = st.form_submit_button(
                "Salvar novo preço base", use_container_width=True
            )

        if salvar_novo:
            faixa_final_salvar = 0.0 if sem_limite_novo else faixa_final_nova
            erros = validar_preco_base(
                tabela_base=tabela_base_nova,
                regime=regime_novo,
                faixa_inicial=faixa_inicial_nova,
                faixa_final=faixa_final_salvar,
                sem_limite_superior=sem_limite_novo,
                valor_base=valor_base_novo,
                registros_existentes=registros,
            )
            if erros:
                for erro in erros:
                    st.warning(erro)
            else:
                try:
                    dados = {
                        "tabela_base": tabela_base_nova.strip(),
                        "regime": regime_novo.strip(),
                        "faixa_inicial": float(faixa_inicial_nova),
                        "faixa_final": faixa_final_salvar,
                        "sem_limite_superior": sem_limite_novo,
                        "valor_base": float(valor_base_novo),
                        "ativo": True,
                        "observacao": observacao_nova.strip() or None,
                    }
                    supabase.table("precos_base_precificacao").insert(dados).execute()
                    limpar_cache_precos_base()
                    st.success("Preço base cadastrado com sucesso.")
                    st.rerun()
                except Exception as erro:
                    st.error(f"Erro ao cadastrar o preço base: {erro}")

    with aba_editar:
        st.markdown("### Editar preço base")
        registros_ativos = [registro for registro in registros if registro.get("ativo")]
        if not registros_ativos:
            st.info("Não existem preços base ativos para editar.")
        else:
            opcoes = {
                (
                    f"{registro.get('id')} | {registro.get('tabela_base')} | "
                    f"{registro.get('regime')} | {formatar_faixa_preco(registro)} | "
                    f"R$ {float(registro.get('valor_base') or 0):.2f}"
                ): registro
                for registro in registros_ativos
            }
            texto_escolhido = st.selectbox(
                "Selecione o preço base",
                list(opcoes.keys()),
                key="admin_preco_editar_select",
            )
            escolhido = opcoes[texto_escolhido]
            registro_id = int(escolhido["id"])

            with st.form(f"form_editar_preco_{registro_id}"):
                tabela_base_editar = st.text_input(
                    "Tabela base", value=str(escolhido.get("tabela_base") or "")
                )
                regime_editar = st.text_input(
                    "Regime tributário", value=str(escolhido.get("regime") or "")
                )
                coluna1, coluna2 = st.columns(2)
                with coluna1:
                    faixa_inicial_editar = st.number_input(
                        "Faixa inicial",
                        min_value=0.0,
                        step=0.01,
                        format="%.2f",
                        value=float(escolhido.get("faixa_inicial") or 0),
                    )
                with coluna2:
                    sem_limite_editar = st.checkbox(
                        "Sem limite superior",
                        value=bool(escolhido.get("sem_limite_superior")),
                    )
                    faixa_final_editar = st.number_input(
                        "Faixa final",
                        min_value=0.0,
                        step=0.01,
                        format="%.2f",
                        value=float(escolhido.get("faixa_final") or 0),
                        disabled=sem_limite_editar,
                    )
                valor_base_editar = st.number_input(
                    "Valor base (R$)",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    value=float(escolhido.get("valor_base") or 0),
                )
                observacao_editar = st.text_area(
                    "Observação",
                    value=str(escolhido.get("observacao") or ""),
                    height=80,
                )
                salvar_edicao = st.form_submit_button(
                    "Salvar alterações", use_container_width=True
                )

            if salvar_edicao:
                faixa_final_salvar = 0.0 if sem_limite_editar else faixa_final_editar
                erros = validar_preco_base(
                    tabela_base=tabela_base_editar,
                    regime=regime_editar,
                    faixa_inicial=faixa_inicial_editar,
                    faixa_final=faixa_final_salvar,
                    sem_limite_superior=sem_limite_editar,
                    valor_base=valor_base_editar,
                    registros_existentes=registros,
                    registro_id_edicao=registro_id,
                )
                if erros:
                    for erro in erros:
                        st.warning(erro)
                else:
                    try:
                        dados = {
                            "tabela_base": tabela_base_editar.strip(),
                            "regime": regime_editar.strip(),
                            "faixa_inicial": float(faixa_inicial_editar),
                            "faixa_final": faixa_final_salvar,
                            "sem_limite_superior": sem_limite_editar,
                            "valor_base": float(valor_base_editar),
                            "observacao": observacao_editar.strip() or None,
                        }
                        (
                            supabase
                            .table("precos_base_precificacao")
                            .update(dados)
                            .eq("id", registro_id)
                            .execute()
                        )
                        limpar_cache_precos_base()
                        st.success("Preço base atualizado com sucesso.")
                        st.rerun()
                    except Exception as erro:
                        st.error(f"Erro ao atualizar o preço base: {erro}")

            st.divider()
            st.markdown("### Inativar preço base")
            confirmar = st.checkbox(
                "Confirmo que desejo inativar o preço base selecionado",
                key=f"confirmar_inativar_preco_{registro_id}",
            )
            if st.button(
                "Inativar preço base",
                disabled=not confirmar,
                use_container_width=True,
                key=f"inativar_preco_{registro_id}",
            ):
                try:
                    (
                        supabase
                        .table("precos_base_precificacao")
                        .update({"ativo": False})
                        .eq("id", registro_id)
                        .execute()
                    )
                    limpar_cache_precos_base()
                    st.success("Preço base inativado com sucesso.")
                    st.rerun()
                except Exception as erro:
                    st.error(f"Erro ao inativar o preço base: {erro}")

    with aba_copiar:
        st.markdown("### Copiar preço base")
        ativos = [registro for registro in registros if registro.get("ativo")]
        if not ativos:
            st.info("Não existem preços base ativos para copiar.")
        else:
            opcoes_copia = {
                (
                    f"{registro.get('id')} | {registro.get('tabela_base')} | "
                    f"{registro.get('regime')} | {formatar_faixa_preco(registro)}"
                ): registro
                for registro in ativos
            }
            origem_texto = st.selectbox(
                "Selecione o preço de origem",
                list(opcoes_copia.keys()),
                key="admin_preco_copiar_origem",
            )
            origem = opcoes_copia[origem_texto]

            with st.form("form_copiar_preco_base"):
                nova_tabela = st.text_input(
                    "Nova tabela base", value=str(origem.get("tabela_base") or "")
                )
                novo_regime = st.text_input(
                    "Novo regime", value=str(origem.get("regime") or "")
                )
                novo_valor = st.number_input(
                    "Novo valor base (R$)",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    value=float(origem.get("valor_base") or 0),
                )
                nova_observacao = st.text_area(
                    "Observação",
                    value=f"Cópia do registro {origem.get('id')}",
                    height=80,
                )
                copiar = st.form_submit_button("Criar cópia", use_container_width=True)

            if copiar:
                erros = validar_preco_base(
                    tabela_base=nova_tabela,
                    regime=novo_regime,
                    faixa_inicial=origem.get("faixa_inicial"),
                    faixa_final=origem.get("faixa_final"),
                    sem_limite_superior=bool(origem.get("sem_limite_superior")),
                    valor_base=novo_valor,
                    registros_existentes=registros,
                )
                if erros:
                    for erro in erros:
                        st.warning(erro)
                else:
                    try:
                        dados = {
                            "tabela_base": nova_tabela.strip(),
                            "regime": novo_regime.strip(),
                            "faixa_inicial": origem.get("faixa_inicial"),
                            "faixa_final": origem.get("faixa_final"),
                            "sem_limite_superior": bool(origem.get("sem_limite_superior")),
                            "valor_base": float(novo_valor),
                            "ativo": True,
                            "observacao": nova_observacao.strip() or None,
                        }
                        supabase.table("precos_base_precificacao").insert(dados).execute()
                        limpar_cache_precos_base()
                        st.success("Cópia criada com sucesso.")
                        st.rerun()
                    except Exception as erro:
                        st.error(f"Erro ao copiar o preço base: {erro}")
