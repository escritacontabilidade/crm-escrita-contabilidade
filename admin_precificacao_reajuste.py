import pandas as pd
import streamlit as st

from admin_precificacao_reajuste_service import (
    aplicar_reajuste_com_backup,
    gerar_previa_reajuste,
)


SEGMENTOS_PRECIFICACAO = [
    "Comércio",
    "Geral Completo",
    "Holding",
    "Importadoras",
    "Indústria",
    "Prestadoras de Serviço",
    "Serviços - Clinica Médica",
]


def formatar_moeda_br(valor):
    valor = float(valor or 0)
    texto = f"{valor:,.2f}"

    return (
        "R$ "
        + texto
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def limpar_previa_anterior():
    st.session_state.pop("reajuste_previa", None)


def montar_configuracao(
    tipo_reajuste,
    valor_reajuste,
    aplicar_precos_base,
    aplicar_faixas,
    aplicar_regras_valor_fixo,
    aplicar_todos_segmentos,
    segmentos_escolhidos,
    arredondamento,
    motivo,
    observacoes,
):
    return {
        "tipo": tipo_reajuste,
        "valor": float(valor_reajuste),
        "aplicar_precos_base": aplicar_precos_base,
        "aplicar_faixas": aplicar_faixas,
        "aplicar_regras_valor_fixo": aplicar_regras_valor_fixo,
        "todos_segmentos": aplicar_todos_segmentos,
        "segmentos": segmentos_escolhidos,
        "arredondamento": arredondamento,
        "motivo": motivo.strip(),
        "observacoes": observacoes.strip(),
    }


def validar_configuracao(configuracao):
    erros = []

    if not any([
        configuracao["aplicar_precos_base"],
        configuracao["aplicar_faixas"],
        configuracao["aplicar_regras_valor_fixo"],
    ]):
        erros.append(
            "Selecione pelo menos um grupo para reajustar."
        )

    if (
        not configuracao["todos_segmentos"]
        and not configuracao["segmentos"]
    ):
        erros.append(
            "Selecione pelo menos um segmento."
        )

    if not configuracao["motivo"]:
        erros.append(
            "Informe o motivo do reajuste."
        )

    return erros


def exibir_resumo_previa(preview):
    resumo = preview["resumo"]

    st.markdown("### Resumo da prévia")

    coluna1, coluna2, coluna3 = st.columns(3)

    coluna1.metric(
        "Registros encontrados",
        resumo["total_encontrados"],
    )

    coluna2.metric(
        "Registros alterados",
        resumo["total_alterados"],
    )

    coluna3.metric(
        "Permanecerão iguais",
        resumo["total_iguais"],
    )

    coluna4, coluna5, coluna6 = st.columns(3)

    coluna4.metric(
        "Soma dos valores atuais",
        formatar_moeda_br(resumo["total_antes"]),
    )

    coluna5.metric(
        "Soma dos valores novos",
        formatar_moeda_br(resumo["total_depois"]),
    )

    coluna6.metric(
        "Diferença total",
        formatar_moeda_br(resumo["diferenca_total"]),
    )


def exibir_tabela_previa(preview):
    itens = preview["itens"]

    if not itens:
        st.warning(
            "Nenhum registro ativo foi encontrado "
            "com os filtros selecionados."
        )
        return

    linhas = []

    for item in itens:
        linhas.append({
            "Tipo": item["tipo"],
            "Segmento": item["segmento"],
            "Descrição": item["descricao"],
            "Valor atual": item["valor_atual"],
            "Valor novo": item["valor_novo"],
            "Diferença": item["diferenca"],
            "Será alterado": (
                "Sim" if item["alterado"] else "Não"
            ),
        })

    st.markdown("### Comparação antes x depois")

    st.dataframe(
        pd.DataFrame(linhas),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Valor atual": st.column_config.NumberColumn(
                "Valor atual",
                format="R$ %.2f",
            ),
            "Valor novo": st.column_config.NumberColumn(
                "Valor novo",
                format="R$ %.2f",
            ),
            "Diferença": st.column_config.NumberColumn(
                "Diferença",
                format="R$ %.2f",
            ),
        },
    )


def renderizar_area_aplicacao(
    supabase,
    preview,
    configuracao,
):
    st.divider()
    st.markdown("## Aplicar reajuste")

    st.error(
        "Esta operação altera os valores reais da precificação."
    )

    confirmar = st.checkbox(
        "Confirmo que revisei a prévia e desejo aplicar o reajuste",
        key="reajuste_confirmar_aplicacao",
    )

    texto_confirmacao = st.text_input(
        "Digite APLICAR para liberar o botão",
        key="reajuste_texto_confirmacao",
    )

    liberado = (
        confirmar
        and texto_confirmacao.strip().upper() == "APLICAR"
        and preview["resumo"]["total_alterados"] > 0
    )

    if st.button(
        "Aplicar Reajuste",
        disabled=not liberado,
        type="primary",
        use_container_width=True,
        key="reajuste_aplicar",
    ):
        try:
            with st.spinner(
                "Criando backup e aplicando o reajuste..."
            ):
                resultado = aplicar_reajuste_com_backup(
                    supabase=supabase,
                    preview=preview,
                    configuracao=configuracao,
                    criado_por=st.session_state.get(
                        "perfil_usuario",
                        "Sistema",
                    ),
                )

            st.cache_data.clear()
            limpar_previa_anterior()

            st.success("Reajuste aplicado com sucesso.")
            st.write(
                f"Backup criado: "
                f"{resultado.get('backup_id') or '-'}"
            )
            st.write(
                f"Registros atualizados: "
                f"{resultado.get('total_enviado')}"
            )
            st.info(
                "Gere uma nova prévia para conferir "
                "os valores atualizados."
            )

        except Exception as erro:
            st.error(
                "O reajuste não foi aplicado: "
                f"{erro}"
            )


def renderizar_aba_reajuste(supabase):
    st.subheader("Reajuste Geral")

    st.info(
        "O sistema calcula uma prévia antes de permitir "
        "qualquer alteração."
    )

    with st.form("form_reajuste_geral"):
        st.markdown("### 1. Tipo de reajuste")

        tipo_reajuste = st.radio(
            "Como deseja calcular o reajuste?",
            options=["Percentual", "Valor fixo"],
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
                key="reajuste_percentual",
            )
        else:
            valor_reajuste = st.number_input(
                "Valor fixo do reajuste (R$)",
                step=1.00,
                value=10.00,
                format="%.2f",
                key="reajuste_valor_fixo",
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
            options=SEGMENTOS_PRECIFICACAO,
            default=[],
            disabled=aplicar_todos_segmentos,
            key="reajuste_segmentos",
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
            placeholder="Exemplo: Reajuste anual 2027",
            max_chars=150,
            key="reajuste_motivo",
        )

        observacoes = st.text_area(
            "Observações",
            height=100,
            key="reajuste_observacoes",
        )

        gerar_previa = st.form_submit_button(
            "Gerar Prévia",
            use_container_width=True,
        )

    if gerar_previa:
        configuracao = montar_configuracao(
            tipo_reajuste=tipo_reajuste,
            valor_reajuste=valor_reajuste,
            aplicar_precos_base=aplicar_precos_base,
            aplicar_faixas=aplicar_faixas,
            aplicar_regras_valor_fixo=(
                aplicar_regras_valor_fixo
            ),
            aplicar_todos_segmentos=(
                aplicar_todos_segmentos
            ),
            segmentos_escolhidos=segmentos_escolhidos,
            arredondamento=arredondamento,
            motivo=motivo,
            observacoes=observacoes,
        )

        erros = validar_configuracao(configuracao)

        if erros:
            limpar_previa_anterior()

            for erro in erros:
                st.warning(erro)
        else:
            try:
                with st.spinner("Calculando a prévia..."):
                    preview = gerar_previa_reajuste(
                        supabase=supabase,
                        configuracao=configuracao,
                    )

                st.session_state["reajuste_previa"] = {
                    "configuracao": configuracao,
                    "resultado": preview,
                }

                st.success(
                    "Prévia calculada. Nenhum valor foi alterado."
                )

            except Exception as erro:
                limpar_previa_anterior()
                st.error(
                    "Não foi possível gerar a prévia: "
                    f"{erro}"
                )

    st.divider()
    st.markdown("## Prévia do reajuste")

    dados_sessao = st.session_state.get("reajuste_previa")

    if not dados_sessao:
        st.info(
            "Preencha os campos e clique em Gerar Prévia."
        )
        return

    preview = dados_sessao["resultado"]
    configuracao = dados_sessao["configuracao"]

    st.caption(
        f"Motivo: {configuracao['motivo']}"
    )

    exibir_resumo_previa(preview)
    exibir_tabela_previa(preview)

    renderizar_area_aplicacao(
        supabase=supabase,
        preview=preview,
        configuracao=configuracao,
    )
