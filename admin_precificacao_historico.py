import pandas as pd
import streamlit as st

from database import (
    criar_backup_precificacao,
    listar_versoes_precificacao,
    obter_versao_precificacao,
)


def restaurar_versao_com_backup(
    supabase,
    versao_id,
    nome_versao,
    criado_por,
):
    """
    Cria um backup da situação atual e depois restaura
    a versão escolhida.
    """
    backup = criar_backup_precificacao(
        supabase=supabase,
        nome=(
            "Backup automático antes da restauração - "
            f"versão {versao_id}"
        ),
        descricao=(
            "Backup criado automaticamente antes de restaurar "
            f"a versão {versao_id}: {nome_versao}"
        ),
        tipo="antes_restauracao",
        percentual_reajuste=None,
        criado_por=criado_por,
    )

    backup_id = None

    if getattr(backup, "data", None):
        backup_id = backup.data[0].get("id")

    resultado = (
        supabase
        .rpc(
            "restaurar_versao_precificacao",
            {"p_versao_id": int(versao_id)},
        )
        .execute()
    )

    return {
        "backup_id": backup_id,
        "resultado": resultado.data,
    }


def renderizar_aba_historico(supabase):
    st.subheader("Histórico de versões")

    try:
        versoes = listar_versoes_precificacao(supabase)
    except Exception as erro:
        st.error(
            f"Não foi possível carregar o histórico: {erro}"
        )
        return

    if not versoes:
        st.info(
            "Nenhuma versão foi criada ainda. "
            "Os backups aparecerão aqui."
        )
        return

    linhas = []

    for versao in versoes:
        linhas.append({
            "ID": versao.get("id"),
            "Nome": versao.get("nome"),
            "Tipo": versao.get("tipo"),
            "Reajuste (%)": versao.get(
                "percentual_reajuste"
            ),
            "Preços base": versao.get(
                "quantidade_precos_base"
            ),
            "Regras": versao.get(
                "quantidade_regras"
            ),
            "Faixas": versao.get(
                "quantidade_faixas"
            ),
            "Criado por": versao.get("criado_por"),
            "Criado em": versao.get("criado_em"),
            "Restaurada em": versao.get(
                "restaurada_em"
            ),
        })

    st.dataframe(
        pd.DataFrame(linhas),
        use_container_width=True,
        hide_index=True,
    )

    opcoes = {
        (
            f"{versao.get('id')} | "
            f"{versao.get('nome')}"
        ): versao
        for versao in versoes
    }

    versao_escolhida_texto = st.selectbox(
        "Selecione uma versão",
        list(opcoes.keys()),
        key="admin_historico_versao",
    )

    versao = opcoes[versao_escolhida_texto]
    versao_id = int(versao["id"])

    try:
        dados = obter_versao_precificacao(
            supabase,
            versao_id,
        )
    except Exception as erro:
        st.error(
            f"Não foi possível abrir a versão: {erro}"
        )
        return

    if not dados:
        st.warning(
            "A versão selecionada não foi encontrada."
        )
        return

    st.markdown("### Informações da versão")

    coluna1, coluna2, coluna3 = st.columns(3)

    coluna1.metric(
        "Preços base",
        dados.get("quantidade_precos_base") or 0,
    )
    coluna2.metric(
        "Regras",
        dados.get("quantidade_regras") or 0,
    )
    coluna3.metric(
        "Faixas",
        dados.get("quantidade_faixas") or 0,
    )

    st.write(
        f"**Nome:** {dados.get('nome') or '-'}"
    )
    st.write(
        f"**Descrição:** {dados.get('descricao') or '-'}"
    )
    st.write(
        f"**Tipo:** {dados.get('tipo') or '-'}"
    )
    st.write(
        f"**Criado por:** {dados.get('criado_por') or '-'}"
    )
    st.write(
        f"**Criado em:** {dados.get('criado_em') or '-'}"
    )

    percentual = dados.get("percentual_reajuste")

    if percentual is not None:
        st.write(
            f"**Percentual de reajuste:** "
            f"{float(percentual):.2f}%"
        )

    st.divider()
    st.markdown("## Restaurar esta versão")

    st.error(
        "A restauração substituirá os preços base, regras e "
        "faixas atuais pelos dados desta versão. Antes disso, "
        "o sistema criará automaticamente um novo backup."
    )

    confirmar = st.checkbox(
        "Confirmo que desejo restaurar esta versão",
        key=f"confirmar_restauracao_{versao_id}",
    )

    texto = st.text_input(
        "Digite RESTAURAR para liberar o botão",
        key=f"texto_restauracao_{versao_id}",
    )

    liberado = (
        confirmar
        and texto.strip().upper() == "RESTAURAR"
    )

    if st.button(
        "Restaurar versão selecionada",
        disabled=not liberado,
        type="primary",
        use_container_width=True,
        key=f"restaurar_versao_{versao_id}",
    ):
        try:
            with st.spinner(
                "Criando backup e restaurando a versão..."
            ):
                retorno = restaurar_versao_com_backup(
                    supabase=supabase,
                    versao_id=versao_id,
                    nome_versao=(
                        dados.get("nome")
                        or f"Versão {versao_id}"
                    ),
                    criado_por=st.session_state.get(
                        "perfil_usuario",
                        "Sistema",
                    ),
                )

            st.cache_data.clear()

            resultado = retorno.get("resultado") or {}

            st.success(
                "Versão restaurada com sucesso."
            )

            st.write(
                f"Backup de segurança criado: "
                f"{retorno.get('backup_id') or '-'}"
            )
            st.write(
                f"Versão restaurada: {versao_id}"
            )

            if isinstance(resultado, dict):
                st.write(
                    "Preços base restaurados: "
                    f"{resultado.get('precos_base_restaurados', '-')}"
                )
                st.write(
                    "Regras restauradas: "
                    f"{resultado.get('regras_restauradas', '-')}"
                )
                st.write(
                    "Faixas restauradas: "
                    f"{resultado.get('faixas_restauradas', '-')}"
                )

            st.info(
                "A precificação atual já corresponde à versão "
                "selecionada."
            )

        except Exception as erro:
            st.error(
                "A versão não foi restaurada: "
                f"{erro}"
            )
