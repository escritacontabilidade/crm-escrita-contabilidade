import pandas as pd
import streamlit as st

from admin_precificacao_reajuste import renderizar_aba_reajuste
from admin_precificacao_historico import renderizar_aba_historico
from admin_precificacao_precos_base import renderizar_aba_precos_base
from admin_precificacao_regras import renderizar_aba_regras


def limpar_cache_precificacao():
    """
    Limpa os dados armazenados temporariamente pelo Streamlit.

    Isso faz com que uma alteração de faixa apareça imediatamente
    no cálculo das propostas.
    """
    st.cache_data.clear()


def numero_para_float(valor):
    """
    Converte valores numéricos para float com segurança.
    """
    if valor is None or valor == "":
        return None

    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def validar_faixa(
    quantidade_inicial,
    quantidade_final,
    valor,
    faixas_existentes,
    faixa_id_edicao=None,
):
    erros = []

    if quantidade_inicial is None:
        erros.append("Informe a quantidade inicial.")
    elif quantidade_inicial < 0:
        erros.append("A quantidade inicial não pode ser negativa.")

    if quantidade_final is not None:
        if quantidade_final < quantidade_inicial:
            erros.append(
                "A quantidade final não pode ser menor "
                "que a quantidade inicial."
            )

    if valor is None:
        erros.append("Informe o valor da faixa.")
    elif valor < 0:
        erros.append("O valor da faixa não pode ser negativo.")

    if erros:
        return erros

    novo_inicio = float(quantidade_inicial)
    novo_final = (
        float(quantidade_final)
        if quantidade_final is not None
        else float("inf")
    )

    for faixa in faixas_existentes:
        faixa_id = faixa.get("id")

        if faixa_id_edicao is not None:
            if int(faixa_id) == int(faixa_id_edicao):
                continue

        existente_inicio = float(
            faixa.get("quantidade_inicial") or 0
        )

        existente_final_original = faixa.get("quantidade_final")
        existente_final = (
            float(existente_final_original)
            if existente_final_original is not None
            else float("inf")
        )

        existe_sobreposicao = (
            novo_inicio <= existente_final
            and novo_final >= existente_inicio
        )

        if existe_sobreposicao:
            erros.append(
                "A nova faixa entra em conflito com uma faixa "
                "já cadastrada."
            )
            break

    return erros


def formatar_intervalo_faixa(linha):
    inicio = linha.get("quantidade_inicial")
    final = linha.get("quantidade_final")

    if inicio is None:
        inicio = 0

    inicio = float(inicio)

    if final is None:
        return f"{inicio:g} ou mais"

    return f"{inicio:g} até {float(final):g}"


def carregar_regras_escalonadas(supabase):
    resposta = (
        supabase
        .table("regras_perguntas_precificacao")
        .select("id, segmento_origem, pergunta, tipo_calculo, ativo")
        .eq("ativo", True)
        .in_("tipo_calculo", ["escalonado", "processos_faixa", "faixas"])
        .order("segmento_origem")
        .order("pergunta")
        .execute()
    )

    return resposta.data or []


def carregar_faixas_regra(supabase, regra_id):
    resposta = (
        supabase
        .table("faixas_precificacao")
        .select("*")
        .eq("regra_pergunta_id", regra_id)
        .eq("ativo", True)
        .order("ordem")
        .order("quantidade_inicial")
        .execute()
    )

    return resposta.data or []


def renderizar_aba_faixas(supabase):
    st.subheader("Faixas de precificação")
    st.info(
        "Consulte, inclua, edite e inative as faixas utilizadas "
        "no cálculo das propostas."
    )

    try:
        regras = carregar_regras_escalonadas(supabase)
    except Exception as erro:
        st.error(f"Não foi possível carregar as regras de precificação: {erro}")
        return

    if not regras:
        st.warning("Nenhuma regra escalonada ativa foi encontrada.")
        return

    segmentos = sorted({
        str(regra.get("segmento_origem") or "").strip()
        for regra in regras
        if regra.get("segmento_origem")
    })

    segmento_escolhido = st.selectbox(
        "Segmento",
        segmentos,
        key="admin_faixas_segmento",
    )

    regras_segmento = [
        regra
        for regra in regras
        if regra.get("segmento_origem") == segmento_escolhido
    ]

    opcoes_regras = {
        f"{regra['id']} | {str(regra.get('pergunta') or '').strip()}": regra
        for regra in regras_segmento
    }

    regra_escolhida_texto = st.selectbox(
        "Pergunta / regra de precificação",
        list(opcoes_regras.keys()),
        key="admin_faixas_regra",
    )

    regra_escolhida = opcoes_regras[regra_escolhida_texto]
    regra_id = int(regra_escolhida["id"])
    st.caption(f"Regra selecionada: ID {regra_id}")

    try:
        faixas = carregar_faixas_regra(supabase, regra_id)
    except Exception as erro:
        st.error(f"Não foi possível carregar as faixas: {erro}")
        return

    st.divider()
    st.subheader("Faixas cadastradas")

    if faixas:
        linhas_tabela = []
        for faixa in faixas:
            linhas_tabela.append({
                "ID": faixa.get("id"),
                "Intervalo": formatar_intervalo_faixa(faixa),
                "Quantidade inicial": faixa.get("quantidade_inicial"),
                "Quantidade final": faixa.get("quantidade_final"),
                "Valor unitário": faixa.get("valor"),
                "Ordem": faixa.get("ordem"),
            })

        st.dataframe(
            pd.DataFrame(linhas_tabela),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("Esta regra ainda não possui faixas ativas.")

    st.divider()
    aba_nova, aba_editar = st.tabs([
        "➕ Nova faixa",
        "✏️ Editar ou inativar",
    ])

    with aba_nova:
        st.subheader("Cadastrar nova faixa")

        with st.form(f"form_nova_faixa_{regra_id}"):
            coluna1, coluna2 = st.columns(2)

            with coluna1:
                nova_quantidade_inicial = st.number_input(
                    "Quantidade inicial",
                    min_value=0.0,
                    step=1.0,
                    value=0.0,
                    key=f"nova_inicio_{regra_id}",
                )

            with coluna2:
                faixa_sem_limite = st.checkbox(
                    "Sem limite superior",
                    value=False,
                    key=f"nova_sem_limite_{regra_id}",
                )

                nova_quantidade_final = st.number_input(
                    "Quantidade final",
                    min_value=0.0,
                    step=1.0,
                    value=0.0,
                    disabled=faixa_sem_limite,
                    key=f"nova_final_{regra_id}",
                )

            nova_valor = st.number_input(
                "Valor unitário da faixa (R$)",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                key=f"nova_valor_{regra_id}",
            )

            ordem_sugerida = max(
                [int(faixa.get("ordem") or 0) for faixa in faixas],
                default=0,
            ) + 1

            nova_ordem = st.number_input(
                "Ordem",
                min_value=1,
                step=1,
                value=ordem_sugerida,
                key=f"nova_ordem_{regra_id}",
            )

            salvar_nova = st.form_submit_button("Salvar nova faixa")

            if salvar_nova:
                quantidade_final_salvar = None if faixa_sem_limite else nova_quantidade_final

                erros = validar_faixa(
                    quantidade_inicial=nova_quantidade_inicial,
                    quantidade_final=quantidade_final_salvar,
                    valor=nova_valor,
                    faixas_existentes=faixas,
                )

                if erros:
                    for erro in erros:
                        st.warning(erro)
                else:
                    try:
                        dados_nova_faixa = {
                            "regra_pergunta_id": regra_id,
                            "quantidade_inicial": nova_quantidade_inicial,
                            "quantidade_final": quantidade_final_salvar,
                            "valor": nova_valor,
                            "ordem": int(nova_ordem),
                            "ativo": True,
                        }

                        (
                            supabase
                            .table("faixas_precificacao")
                            .insert(dados_nova_faixa)
                            .execute()
                        )

                        limpar_cache_precificacao()
                        st.success("Nova faixa cadastrada com sucesso.")
                        st.rerun()

                    except Exception as erro:
                        st.error(f"Erro ao cadastrar a faixa: {erro}")

    with aba_editar:
        st.subheader("Editar faixa existente")

        if not faixas:
            st.info("Não existem faixas para editar.")
        else:
            opcoes_faixas = {
                (
                    f"{faixa['id']} | "
                    f"{formatar_intervalo_faixa(faixa)} | "
                    f"R$ {float(faixa.get('valor') or 0):.2f}"
                ): faixa
                for faixa in faixas
            }

            faixa_escolhida_texto = st.selectbox(
                "Selecione a faixa",
                list(opcoes_faixas.keys()),
                key=f"editar_faixa_select_{regra_id}",
            )

            faixa_escolhida = opcoes_faixas[faixa_escolhida_texto]
            faixa_id = int(faixa_escolhida["id"])
            quantidade_final_atual = faixa_escolhida.get("quantidade_final")
            sem_limite_atual = quantidade_final_atual is None

            with st.form(f"form_editar_faixa_{faixa_id}"):
                coluna1, coluna2 = st.columns(2)

                with coluna1:
                    editar_quantidade_inicial = st.number_input(
                        "Quantidade inicial",
                        min_value=0.0,
                        step=1.0,
                        value=float(faixa_escolhida.get("quantidade_inicial") or 0),
                        key=f"editar_inicio_{faixa_id}",
                    )

                with coluna2:
                    editar_sem_limite = st.checkbox(
                        "Sem limite superior",
                        value=sem_limite_atual,
                        key=f"editar_sem_limite_{faixa_id}",
                    )

                    editar_quantidade_final = st.number_input(
                        "Quantidade final",
                        min_value=0.0,
                        step=1.0,
                        value=float(quantidade_final_atual or 0),
                        disabled=editar_sem_limite,
                        key=f"editar_final_{faixa_id}",
                    )

                editar_valor = st.number_input(
                    "Valor unitário da faixa (R$)",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    value=float(faixa_escolhida.get("valor") or 0),
                    key=f"editar_valor_{faixa_id}",
                )

                editar_ordem = st.number_input(
                    "Ordem",
                    min_value=1,
                    step=1,
                    value=int(faixa_escolhida.get("ordem") or 1),
                    key=f"editar_ordem_{faixa_id}",
                )

                salvar_edicao = st.form_submit_button("Salvar alterações")

                if salvar_edicao:
                    quantidade_final_salvar = None if editar_sem_limite else editar_quantidade_final

                    erros = validar_faixa(
                        quantidade_inicial=editar_quantidade_inicial,
                        quantidade_final=quantidade_final_salvar,
                        valor=editar_valor,
                        faixas_existentes=faixas,
                        faixa_id_edicao=faixa_id,
                    )

                    if erros:
                        for erro in erros:
                            st.warning(erro)
                    else:
                        try:
                            dados_atualizados = {
                                "quantidade_inicial": editar_quantidade_inicial,
                                "quantidade_final": quantidade_final_salvar,
                                "valor": editar_valor,
                                "ordem": int(editar_ordem),
                            }

                            (
                                supabase
                                .table("faixas_precificacao")
                                .update(dados_atualizados)
                                .eq("id", faixa_id)
                                .execute()
                            )

                            limpar_cache_precificacao()
                            st.success("Faixa atualizada com sucesso.")
                            st.rerun()

                        except Exception as erro:
                            st.error(f"Erro ao atualizar a faixa: {erro}")

            st.divider()
            st.subheader("Inativar faixa")
            st.warning(
                "A faixa não será apagada do banco. Ela ficará "
                "inativa e deixará de ser usada nos cálculos."
            )

            confirmar_inativacao = st.checkbox(
                "Confirmo que desejo inativar a faixa selecionada",
                key=f"confirmar_inativacao_{faixa_id}",
            )

            if st.button(
                "Inativar faixa selecionada",
                disabled=not confirmar_inativacao,
                key=f"inativar_faixa_{faixa_id}",
            ):
                try:
                    (
                        supabase
                        .table("faixas_precificacao")
                        .update({"ativo": False})
                        .eq("id", faixa_id)
                        .execute()
                    )

                    limpar_cache_precificacao()
                    st.success("Faixa inativada com sucesso.")
                    st.rerun()

                except Exception as erro:
                    st.error(f"Erro ao inativar a faixa: {erro}")



def renderizar_aba_em_desenvolvimento(titulo, descricao):
    st.subheader(titulo)
    st.info(descricao)


def tela_admin_precificacao(supabase):
    st.title("⚙️ Administração da Precificação")

    abas = st.tabs([
        "📊 Faixas",
        "💰 Preços Base",
        "⚙️ Regras",
        "📈 Reajuste Geral",
        "🧪 Simulador",
        "📜 Histórico",
    ])

    with abas[0]:
        renderizar_aba_faixas(supabase)

    with abas[1]:
        renderizar_aba_precos_base(supabase)

    with abas[2]:
        renderizar_aba_regras(supabase)

    with abas[3]:
        renderizar_aba_reajuste(supabase)

    with abas[4]:
        renderizar_aba_em_desenvolvimento(
            "Simulador",
            "Nesta área será possível testar a precificação sem criar uma proposta comercial.",
        )

    with abas[5]:
        renderizar_aba_historico(supabase)
