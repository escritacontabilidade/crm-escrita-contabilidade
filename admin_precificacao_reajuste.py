import streamlit as st


def renderizar_aba_reajuste(supabase):
    """
    Exibe a estrutura inicial da tela de Reajuste Geral.

    Nesta etapa, a tela apenas coleta os parâmetros.
    A prévia e a gravação no banco serão implementadas
    nas próximas etapas.
    """
    st.subheader("Reajuste Geral")

    st.info(
        "Configure o reajuste e gere uma prévia antes de alterar "
        "qualquer valor da precificação."
    )

    st.warning(
        "Nesta primeira etapa, nenhum valor será alterado no banco."
    )

    with st.form("form_reajuste_geral"):
        st.markdown("### 1. Tipo de reajuste")

        tipo_reajuste = st.radio(
            "Como deseja calcular o reajuste?",
            options=[
                "Percentual",
                "Valor fixo",
            ],
            horizontal=True,
            key="reajuste_tipo",
        )

        if tipo_reajuste == "Percentual":
            valor_reajuste = st.number_input(
                "Percentual de reajuste",
                min_value=-100.0,
                step=0.10,
                value=10.0,
                format="%.2f",
                help=(
                    "Use valor positivo para aumentar e valor "
                    "negativo para reduzir."
                ),
                key="reajuste_percentual",
            )

            st.caption(
                f"Exemplo: R$ 100,00 passaria para "
                f"R$ {100 * (1 + valor_reajuste / 100):,.2f}."
            )

        else:
            valor_reajuste = st.number_input(
                "Valor fixo do reajuste (R$)",
                step=1.00,
                value=10.00,
                format="%.2f",
                help=(
                    "Use valor positivo para aumentar e valor "
                    "negativo para reduzir."
                ),
                key="reajuste_valor_fixo",
            )

            st.caption(
                f"Exemplo: R$ 100,00 passaria para "
                f"R$ {100 + valor_reajuste:,.2f}."
            )

        st.divider()
        st.markdown("### 2. Aplicar o reajuste em")

        coluna1, coluna2, coluna3 = st.columns(3)

        with coluna1:
            aplicar_precos_base = st.checkbox(
                "Preços Base",
                value=True,
                key="reajuste_aplicar_precos_base",
            )

        with coluna2:
            aplicar_faixas = st.checkbox(
                "Faixas",
                value=True,
                key="reajuste_aplicar_faixas",
            )

        with coluna3:
            aplicar_regras_valor_fixo = st.checkbox(
                "Regras de valor fixo",
                value=True,
                key="reajuste_aplicar_regras_fixas",
            )

        st.divider()
        st.markdown("### 3. Segmentos")

        aplicar_todos_segmentos = st.checkbox(
            "Aplicar em todos os segmentos",
            value=True,
            key="reajuste_todos_segmentos",
        )

        segmentos_escolhidos = st.multiselect(
            "Selecione os segmentos",
            options=[
                "Comércio",
                "Geral Completo",
                "Holding",
                "Importadoras",
                "Indústria",
                "Prestadoras de Serviço",
                "Serviços - Clinica Médica",
            ],
            default=[],
            disabled=aplicar_todos_segmentos,
            key="reajuste_segmentos",
        )

        if aplicar_todos_segmentos:
            st.caption(
                "O reajuste considerará todos os segmentos ativos."
            )
        elif not segmentos_escolhidos:
            st.warning(
                "Selecione pelo menos um segmento."
            )

        st.divider()
        st.markdown("### 4. Arredondamento")

        arredondamento = st.selectbox(
            "Regra de arredondamento",
            options=[
                "Não arredondar",
                "Múltiplo de R$ 1,00",
                "Múltiplo de R$ 5,00",
                "Múltiplo de R$ 10,00",
                "Finalizar em ,90",
                "Finalizar em ,99",
            ],
            key="reajuste_arredondamento",
        )

        st.divider()
        st.markdown("### 5. Identificação do reajuste")

        motivo = st.text_input(
            "Motivo do reajuste",
            placeholder=(
                "Exemplo: Reajuste anual 2027, revisão comercial "
                "ou adequação de custos"
            ),
            max_chars=150,
            key="reajuste_motivo",
        )

        observacoes = st.text_area(
            "Observações",
            placeholder=(
                "Campo opcional para registrar detalhes, "
                "critérios ou justificativas."
            ),
            height=100,
            key="reajuste_observacoes",
        )

        st.divider()
        st.markdown("### 6. Resumo da configuração")

        resumo_coluna1, resumo_coluna2, resumo_coluna3 = st.columns(3)

        resumo_coluna1.metric(
            "Tipo",
            tipo_reajuste,
        )

        if tipo_reajuste == "Percentual":
            resumo_coluna2.metric(
                "Valor",
                f"{valor_reajuste:.2f}%",
            )
        else:
            resumo_coluna2.metric(
                "Valor",
                f"R$ {valor_reajuste:,.2f}",
            )

        resumo_coluna3.metric(
            "Arredondamento",
            arredondamento,
        )

        objetos_selecionados = []

        if aplicar_precos_base:
            objetos_selecionados.append("Preços Base")

        if aplicar_faixas:
            objetos_selecionados.append("Faixas")

        if aplicar_regras_valor_fixo:
            objetos_selecionados.append(
                "Regras de valor fixo"
            )

        st.write(
            "**Itens selecionados:** "
            + (
                ", ".join(objetos_selecionados)
                if objetos_selecionados
                else "Nenhum"
            )
        )

        if aplicar_todos_segmentos:
            st.write("**Segmentos:** Todos")
        else:
            st.write(
                "**Segmentos:** "
                + (
                    ", ".join(segmentos_escolhidos)
                    if segmentos_escolhidos
                    else "Nenhum"
                )
            )

        st.write(
            f"**Motivo:** {motivo.strip() if motivo.strip() else 'Não informado'}"
        )

        st.divider()
        st.markdown("### 7. Próximas ações")

        botao_previa = st.form_submit_button(
            "Gerar Prévia",
            use_container_width=True,
        )

        if botao_previa:
            erros = []

            if not objetos_selecionados:
                erros.append(
                    "Selecione pelo menos um grupo para reajustar."
                )

            if (
                not aplicar_todos_segmentos
                and not segmentos_escolhidos
            ):
                erros.append(
                    "Selecione pelo menos um segmento."
                )

            if not motivo.strip():
                erros.append(
                    "Informe o motivo do reajuste."
                )

            if erros:
                for erro in erros:
                    st.warning(erro)
            else:
                st.success(
                    "Configuração validada. Na próxima etapa, "
                    "este botão carregará os registros e mostrará "
                    "a comparação entre os valores atuais e os "
                    "valores reajustados."
                )

                st.session_state[
                    "reajuste_configuracao_validada"
                ] = {
                    "tipo": tipo_reajuste,
                    "valor": valor_reajuste,
                    "aplicar_precos_base": aplicar_precos_base,
                    "aplicar_faixas": aplicar_faixas,
                    "aplicar_regras_valor_fixo": (
                        aplicar_regras_valor_fixo
                    ),
                    "todos_segmentos": aplicar_todos_segmentos,
                    "segmentos": segmentos_escolhidos,
                    "arredondamento": arredondamento,
                    "motivo": motivo.strip(),
                    "observacoes": observacoes.strip(),
                }

    st.divider()
    st.markdown("### Prévia do reajuste")

    if "reajuste_configuracao_validada" not in st.session_state:
        st.info(
            "Preencha os campos e clique em Gerar Prévia."
        )
    else:
        st.info(
            "A configuração foi validada. A leitura dos valores "
            "do Supabase e o cálculo da prévia serão adicionados "
            "na próxima etapa."
        )

    coluna_simulacao, coluna_aplicacao = st.columns(2)

    with coluna_simulacao:
        st.button(
            "Salvar como Simulação",
            disabled=True,
            use_container_width=True,
            help=(
                "Será habilitado depois que a prévia estiver "
                "calculada."
            ),
            key="reajuste_salvar_simulacao",
        )

    with coluna_aplicacao:
        st.button(
            "Aplicar Reajuste",
            disabled=True,
            use_container_width=True,
            help=(
                "Será habilitado depois que a prévia estiver "
                "calculada e confirmada."
            ),
            key="reajuste_aplicar",
        )
