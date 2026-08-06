import pandas as pd
import streamlit as st


TIPOS_CALCULO = [
    "fixo",
    "por_quantidade",
    "escalonado",
    "processos_faixa",
    "faixas",
]

MODOS_APLICACAO = [
    "resposta_igual",
    "quantidade_maior_que_zero",
    "resposta_preenchida",
]


def limpar_cache_regras():
    st.cache_data.clear()


def carregar_regras(supabase):
    resposta = (
        supabase
        .table("regras_perguntas_precificacao")
        .select("*")
        .order("segmento_origem")
        .order("pergunta")
        .order("id")
        .execute()
    )

    return resposta.data or []


def numero_ou_zero(valor):
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def texto_limpo(valor):
    return str(valor or "").strip()


def validar_regra(
    segmento_origem,
    pergunta,
    tipo_calculo,
    modo_aplicacao,
    resposta_gatilho,
    valor_fixo,
    valor_unitario,
    valor_ate_29,
    valor_a_partir_30,
    valor_ate_100,
    valor_101_500,
    valor_acima_500,
    regras_existentes,
    regra_id_edicao=None,
):
    erros = []

    segmento_origem = texto_limpo(segmento_origem)
    pergunta = texto_limpo(pergunta)
    tipo_calculo = texto_limpo(tipo_calculo)
    modo_aplicacao = texto_limpo(modo_aplicacao)
    resposta_gatilho = texto_limpo(resposta_gatilho)

    if not segmento_origem:
        erros.append("Informe o segmento de origem.")

    if not pergunta:
        erros.append("Informe a pergunta.")

    if tipo_calculo not in TIPOS_CALCULO:
        erros.append("Selecione um tipo de cálculo válido.")

    if modo_aplicacao not in MODOS_APLICACAO:
        erros.append("Selecione um modo de aplicação válido.")

    if modo_aplicacao == "resposta_igual" and not resposta_gatilho:
        erros.append(
            "Informe a resposta gatilho para o modo "
            "'resposta igual'."
        )

    campos_numericos = {
        "Valor fixo": valor_fixo,
        "Valor unitário": valor_unitario,
        "Valor até 29": valor_ate_29,
        "Valor a partir de 30": valor_a_partir_30,
        "Valor até 100": valor_ate_100,
        "Valor de 101 a 500": valor_101_500,
        "Valor acima de 500": valor_acima_500,
    }

    for nome, valor in campos_numericos.items():
        if numero_ou_zero(valor) < 0:
            erros.append(f"{nome} não pode ser negativo.")

    if tipo_calculo == "fixo" and numero_ou_zero(valor_fixo) <= 0:
        erros.append(
            "Para regra fixa, informe um valor fixo maior que zero."
        )

    if (
        tipo_calculo == "por_quantidade"
        and numero_ou_zero(valor_unitario) <= 0
    ):
        erros.append(
            "Para cálculo por quantidade, informe um valor "
            "unitário maior que zero."
        )

    if tipo_calculo == "escalonado":
        sem_valor_legado = (
            numero_ou_zero(valor_ate_29) <= 0
            and numero_ou_zero(valor_a_partir_30) <= 0
        )

        if sem_valor_legado:
            # Regras escalonadas também podem usar faixas dinâmicas.
            # Neste caso, a regra pode ser criada com valores zerados.
            pass

    if tipo_calculo == "processos_faixa":
        sem_valores = (
            numero_ou_zero(valor_ate_100) <= 0
            and numero_ou_zero(valor_101_500) <= 0
            and numero_ou_zero(valor_acima_500) <= 0
        )

        if sem_valores:
            erros.append(
                "Informe ao menos um valor para as faixas "
                "de processos."
            )

    for regra in regras_existentes:
        if regra_id_edicao is not None:
            if int(regra.get("id")) == int(regra_id_edicao):
                continue

        mesmo_segmento = (
            texto_limpo(regra.get("segmento_origem")).lower()
            == segmento_origem.lower()
        )

        mesma_pergunta = (
            texto_limpo(regra.get("pergunta")).lower()
            == pergunta.lower()
        )

        if mesmo_segmento and mesma_pergunta:
            erros.append(
                "Já existe uma regra com esta pergunta neste segmento."
            )
            break

    return erros


def montar_linha_tabela(regra):
    return {
        "ID": regra.get("id"),
        "Segmento": regra.get("segmento_origem"),
        "Pergunta": regra.get("pergunta"),
        "Tipo": regra.get("tipo_calculo"),
        "Modo": regra.get("modo_aplicacao"),
        "Gatilho": regra.get("resposta_gatilho"),
        "Valor fixo": regra.get("valor_fixo"),
        "Valor unitário": regra.get("valor_unitario"),
        "Até 29": regra.get("valor_ate_29"),
        "A partir de 30": regra.get("valor_a_partir_30"),
        "Até 100": regra.get("valor_ate_100"),
        "101 a 500": regra.get("valor_101_500"),
        "Acima de 500": regra.get("valor_acima_500"),
        "Ativo": "Sim" if regra.get("ativo") else "Não",
    }


def renderizar_tabela_regras(regras):
    if not regras:
        st.info("Nenhuma regra encontrada.")
        return

    dataframe = pd.DataFrame([
        montar_linha_tabela(regra)
        for regra in regras
    ])

    st.dataframe(
        dataframe,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Valor fixo": st.column_config.NumberColumn(
                "Valor fixo",
                format="R$ %.2f",
            ),
            "Valor unitário": st.column_config.NumberColumn(
                "Valor unitário",
                format="R$ %.2f",
            ),
            "Até 29": st.column_config.NumberColumn(
                "Até 29",
                format="R$ %.2f",
            ),
            "A partir de 30": st.column_config.NumberColumn(
                "A partir de 30",
                format="R$ %.2f",
            ),
            "Até 100": st.column_config.NumberColumn(
                "Até 100",
                format="R$ %.2f",
            ),
            "101 a 500": st.column_config.NumberColumn(
                "101 a 500",
                format="R$ %.2f",
            ),
            "Acima de 500": st.column_config.NumberColumn(
                "Acima de 500",
                format="R$ %.2f",
            ),
        },
    )


def campos_regra_formulario(
    prefixo,
    regra=None,
):
    regra = regra or {}

    segmento = st.text_input(
        "Segmento de origem",
        value=texto_limpo(
            regra.get("segmento_origem")
        ),
        key=f"{prefixo}_segmento",
    )

    pergunta = st.text_area(
        "Pergunta",
        value=texto_limpo(
            regra.get("pergunta")
        ),
        height=100,
        key=f"{prefixo}_pergunta",
    )

    coluna1, coluna2 = st.columns(2)

    with coluna1:
        tipo_atual = texto_limpo(
            regra.get("tipo_calculo")
        )

        tipo_index = (
            TIPOS_CALCULO.index(tipo_atual)
            if tipo_atual in TIPOS_CALCULO
            else 0
        )

        tipo_calculo = st.selectbox(
            "Tipo de cálculo",
            TIPOS_CALCULO,
            index=tipo_index,
            key=f"{prefixo}_tipo",
        )

    with coluna2:
        modo_atual = texto_limpo(
            regra.get("modo_aplicacao")
        )

        modo_index = (
            MODOS_APLICACAO.index(modo_atual)
            if modo_atual in MODOS_APLICACAO
            else 0
        )

        modo_aplicacao = st.selectbox(
            "Modo de aplicação",
            MODOS_APLICACAO,
            index=modo_index,
            key=f"{prefixo}_modo",
        )

    resposta_gatilho = st.text_input(
        "Resposta gatilho",
        value=texto_limpo(
            regra.get("resposta_gatilho")
        ),
        help=(
            "Usado principalmente quando o modo de aplicação "
            "for 'resposta_igual'."
        ),
        key=f"{prefixo}_gatilho",
    )

    st.markdown("#### Valores da regra")

    valor1, valor2 = st.columns(2)

    with valor1:
        valor_fixo = st.number_input(
            "Valor fixo (R$)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            value=numero_ou_zero(
                regra.get("valor_fixo")
            ),
            key=f"{prefixo}_valor_fixo",
        )

    with valor2:
        valor_unitario = st.number_input(
            "Valor unitário (R$)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            value=numero_ou_zero(
                regra.get("valor_unitario")
            ),
            key=f"{prefixo}_valor_unitario",
        )

    st.markdown("#### Valores escalonados antigos")

    escala1, escala2 = st.columns(2)

    with escala1:
        valor_ate_29 = st.number_input(
            "Valor até 29 (R$)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            value=numero_ou_zero(
                regra.get("valor_ate_29")
            ),
            key=f"{prefixo}_valor_ate_29",
        )

    with escala2:
        valor_a_partir_30 = st.number_input(
            "Valor a partir de 30 (R$)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            value=numero_ou_zero(
                regra.get("valor_a_partir_30")
            ),
            key=f"{prefixo}_valor_a_partir_30",
        )

    st.markdown("#### Valores para processos")

    processo1, processo2, processo3 = st.columns(3)

    with processo1:
        valor_ate_100 = st.number_input(
            "Valor até 100 (R$)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            value=numero_ou_zero(
                regra.get("valor_ate_100")
            ),
            key=f"{prefixo}_valor_ate_100",
        )

    with processo2:
        valor_101_500 = st.number_input(
            "Valor de 101 a 500 (R$)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            value=numero_ou_zero(
                regra.get("valor_101_500")
            ),
            key=f"{prefixo}_valor_101_500",
        )

    with processo3:
        valor_acima_500 = st.number_input(
            "Valor acima de 500 (R$)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            value=numero_ou_zero(
                regra.get("valor_acima_500")
            ),
            key=f"{prefixo}_valor_acima_500",
        )

    return {
        "segmento_origem": segmento,
        "pergunta": pergunta,
        "tipo_calculo": tipo_calculo,
        "modo_aplicacao": modo_aplicacao,
        "resposta_gatilho": resposta_gatilho,
        "valor_fixo": valor_fixo,
        "valor_unitario": valor_unitario,
        "valor_ate_29": valor_ate_29,
        "valor_a_partir_30": valor_a_partir_30,
        "valor_ate_100": valor_ate_100,
        "valor_101_500": valor_101_500,
        "valor_acima_500": valor_acima_500,
    }


def normalizar_dados_regra(dados):
    return {
        "segmento_origem": texto_limpo(
            dados["segmento_origem"]
        ),
        "pergunta": texto_limpo(
            dados["pergunta"]
        ),
        "tipo_calculo": texto_limpo(
            dados["tipo_calculo"]
        ),
        "modo_aplicacao": texto_limpo(
            dados["modo_aplicacao"]
        ),
        "resposta_gatilho": (
            texto_limpo(
                dados["resposta_gatilho"]
            )
            or None
        ),
        "valor_fixo": float(
            dados["valor_fixo"]
        ),
        "valor_unitario": float(
            dados["valor_unitario"]
        ),
        "valor_ate_29": float(
            dados["valor_ate_29"]
        ),
        "valor_a_partir_30": float(
            dados["valor_a_partir_30"]
        ),
        "valor_ate_100": float(
            dados["valor_ate_100"]
        ),
        "valor_101_500": float(
            dados["valor_101_500"]
        ),
        "valor_acima_500": float(
            dados["valor_acima_500"]
        ),
    }


def renderizar_aba_regras(supabase):
    st.subheader("Regras de Precificação")

    st.info(
        "Consulte, filtre, cadastre, edite, copie e "
        "ative ou inative as regras usadas no cálculo."
    )

    try:
        regras = carregar_regras(supabase)
    except Exception as erro:
        st.error(
            f"Não foi possível carregar as regras: {erro}"
        )
        return

    segmentos = sorted({
        texto_limpo(
            regra.get("segmento_origem")
        )
        for regra in regras
        if texto_limpo(
            regra.get("segmento_origem")
        )
    })

    tipos = sorted({
        texto_limpo(
            regra.get("tipo_calculo")
        )
        for regra in regras
        if texto_limpo(
            regra.get("tipo_calculo")
        )
    })

    st.markdown("### Consulta")

    filtro1, filtro2, filtro3 = st.columns(3)

    with filtro1:
        pesquisa = st.text_input(
            "Pesquisar",
            placeholder=(
                "Pergunta, segmento, tipo ou gatilho"
            ),
            key="admin_regras_pesquisa",
        )

    with filtro2:
        segmento_filtro = st.selectbox(
            "Segmento",
            ["Todos"] + segmentos,
            key="admin_regras_segmento",
        )

    with filtro3:
        tipo_filtro = st.selectbox(
            "Tipo de cálculo",
            ["Todos"] + tipos,
            key="admin_regras_tipo",
        )

    mostrar_inativas = st.checkbox(
        "Mostrar regras inativas",
        value=False,
        key="admin_regras_inativas",
    )

    termo = pesquisa.strip().lower()
    regras_filtradas = []

    for regra in regras:
        ativo = bool(regra.get("ativo"))

        if not mostrar_inativas and not ativo:
            continue

        if (
            segmento_filtro != "Todos"
            and regra.get("segmento_origem")
            != segmento_filtro
        ):
            continue

        if (
            tipo_filtro != "Todos"
            and regra.get("tipo_calculo")
            != tipo_filtro
        ):
            continue

        texto_busca = " ".join([
            texto_limpo(regra.get("id")),
            texto_limpo(
                regra.get("segmento_origem")
            ),
            texto_limpo(
                regra.get("pergunta")
            ),
            texto_limpo(
                regra.get("tipo_calculo")
            ),
            texto_limpo(
                regra.get("modo_aplicacao")
            ),
            texto_limpo(
                regra.get("resposta_gatilho")
            ),
        ]).lower()

        if termo and termo not in texto_busca:
            continue

        regras_filtradas.append(regra)

    st.caption(
        f"{len(regras_filtradas)} regra(s) encontrada(s)."
    )

    renderizar_tabela_regras(
        regras_filtradas
    )

    exportacao = pd.DataFrame([
        montar_linha_tabela(regra)
        for regra in regras_filtradas
    ])

    st.download_button(
        "Exportar consulta para CSV",
        data=exportacao.to_csv(
            index=False
        ).encode("utf-8-sig"),
        file_name=(
            "regras_precificacao.csv"
        ),
        mime="text/csv",
        use_container_width=True,
    )

    st.divider()

    aba_nova, aba_editar, aba_copiar = st.tabs([
        "➕ Nova regra",
        "✏️ Editar ou ativar/inativar",
        "📋 Copiar regra",
    ])

    with aba_nova:
        st.markdown("### Cadastrar nova regra")

        with st.form("form_nova_regra"):
            dados_nova = campos_regra_formulario(
                "nova_regra"
            )

            salvar_nova = (
                st.form_submit_button(
                    "Salvar nova regra",
                    use_container_width=True,
                )
            )

        if salvar_nova:
            erros = validar_regra(
                regras_existentes=regras,
                **dados_nova,
            )

            if erros:
                for erro in erros:
                    st.warning(erro)
            else:
                try:
                    dados_salvar = (
                        normalizar_dados_regra(
                            dados_nova
                        )
                    )

                    dados_salvar["ativo"] = True

                    (
                        supabase
                        .table(
                            "regras_perguntas_precificacao"
                        )
                        .insert(dados_salvar)
                        .execute()
                    )

                    limpar_cache_regras()

                    st.success(
                        "Regra cadastrada com sucesso."
                    )

                    st.rerun()

                except Exception as erro:
                    st.error(
                        f"Erro ao cadastrar a regra: {erro}"
                    )

    with aba_editar:
        st.markdown("### Editar regra existente")

        if not regras:
            st.info(
                "Não existem regras cadastradas."
            )
        else:
            opcoes = {
                (
                    f"{regra.get('id')} | "
                    f"{regra.get('segmento_origem')} | "
                    f"{regra.get('pergunta')}"
                ): regra
                for regra in regras
            }

            texto_escolhido = st.selectbox(
                "Selecione a regra",
                list(opcoes.keys()),
                key="admin_regras_editar_select",
            )

            regra_escolhida = opcoes[
                texto_escolhido
            ]

            regra_id = int(
                regra_escolhida["id"]
            )

            with st.form(
                f"form_editar_regra_{regra_id}"
            ):
                dados_editar = (
                    campos_regra_formulario(
                        f"editar_regra_{regra_id}",
                        regra_escolhida,
                    )
                )

                salvar_edicao = (
                    st.form_submit_button(
                        "Salvar alterações",
                        use_container_width=True,
                    )
                )

            if salvar_edicao:
                erros = validar_regra(
                    regras_existentes=regras,
                    regra_id_edicao=regra_id,
                    **dados_editar,
                )

                if erros:
                    for erro in erros:
                        st.warning(erro)
                else:
                    try:
                        dados_salvar = (
                            normalizar_dados_regra(
                                dados_editar
                            )
                        )

                        (
                            supabase
                            .table(
                                "regras_perguntas_precificacao"
                            )
                            .update(dados_salvar)
                            .eq("id", regra_id)
                            .execute()
                        )

                        limpar_cache_regras()

                        st.success(
                            "Regra atualizada com sucesso."
                        )

                        st.rerun()

                    except Exception as erro:
                        st.error(
                            "Erro ao atualizar a regra: "
                            f"{erro}"
                        )

            st.divider()

            ativo_atual = bool(
                regra_escolhida.get("ativo")
            )

            if ativo_atual:
                st.markdown(
                    "### Inativar regra"
                )

                confirmar = st.checkbox(
                    "Confirmo que desejo inativar "
                    "a regra selecionada",
                    key=(
                        f"confirmar_inativar_"
                        f"regra_{regra_id}"
                    ),
                )

                texto_botao = (
                    "Inativar regra selecionada"
                )

                novo_status = False
            else:
                st.markdown(
                    "### Reativar regra"
                )

                confirmar = st.checkbox(
                    "Confirmo que desejo reativar "
                    "a regra selecionada",
                    key=(
                        f"confirmar_reativar_"
                        f"regra_{regra_id}"
                    ),
                )

                texto_botao = (
                    "Reativar regra selecionada"
                )

                novo_status = True

            if st.button(
                texto_botao,
                disabled=not confirmar,
                use_container_width=True,
                key=(
                    f"alterar_status_regra_"
                    f"{regra_id}"
                ),
            ):
                try:
                    (
                        supabase
                        .table(
                            "regras_perguntas_precificacao"
                        )
                        .update({
                            "ativo": novo_status
                        })
                        .eq("id", regra_id)
                        .execute()
                    )

                    limpar_cache_regras()

                    st.success(
                        "Status da regra alterado "
                        "com sucesso."
                    )

                    st.rerun()

                except Exception as erro:
                    st.error(
                        "Erro ao alterar o status "
                        f"da regra: {erro}"
                    )

    with aba_copiar:
        st.markdown("### Copiar regra")

        regras_ativas = [
            regra
            for regra in regras
            if regra.get("ativo")
        ]

        if not regras_ativas:
            st.info(
                "Não existem regras ativas para copiar."
            )
        else:
            opcoes_copia = {
                (
                    f"{regra.get('id')} | "
                    f"{regra.get('segmento_origem')} | "
                    f"{regra.get('pergunta')}"
                ): regra
                for regra in regras_ativas
            }

            origem_texto = st.selectbox(
                "Selecione a regra de origem",
                list(opcoes_copia.keys()),
                key="admin_regras_copiar_origem",
            )

            origem = opcoes_copia[
                origem_texto
            ]

            st.caption(
                "Os valores serão copiados. "
                "Altere ao menos o segmento ou a pergunta."
            )

            with st.form("form_copiar_regra"):
                dados_copia = (
                    campos_regra_formulario(
                        "copiar_regra",
                        origem,
                    )
                )

                copiar = (
                    st.form_submit_button(
                        "Criar cópia",
                        use_container_width=True,
                    )
                )

            if copiar:
                erros = validar_regra(
                    regras_existentes=regras,
                    **dados_copia,
                )

                if erros:
                    for erro in erros:
                        st.warning(erro)
                else:
                    try:
                        dados_salvar = (
                            normalizar_dados_regra(
                                dados_copia
                            )
                        )

                        dados_salvar["ativo"] = True

                        (
                            supabase
                            .table(
                                "regras_perguntas_precificacao"
                            )
                            .insert(dados_salvar)
                            .execute()
                        )

                        limpar_cache_regras()

                        st.success(
                            "Cópia criada com sucesso."
                        )

                        st.rerun()

                    except Exception as erro:
                        st.error(
                            "Erro ao copiar a regra: "
                            f"{erro}"
                        )
