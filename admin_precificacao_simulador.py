import json

import pandas as pd
import streamlit as st

from database import (
    get_perguntas_por_origem,
    get_regras_precificacao,
)
from pricing import calcular_preco_completo


def texto_limpo(valor):
    return str(valor or "").strip()


def formatar_moeda(valor):
    valor = float(valor or 0)

    texto = f"{valor:,.2f}"

    return (
        "R$ "
        + texto
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def carregar_segmentos_simulador(supabase):
    resposta = (
        supabase
        .table("regras_segmento")
        .select("*")
        .order("segmentos")
        .execute()
    )

    return resposta.data or []


def carregar_mapa_segmentos_simulador(supabase):
    resposta = (
        supabase
        .table("mapa_segmento_precificacao")
        .select("segmento_questionario,tabela_base,ativo")
        .eq("ativo", True)
        .execute()
    )

    return resposta.data or []


def carregar_precos_base(supabase):
    resposta = (
        supabase
        .table("precos_base_precificacao")
        .select("*")
        .eq("ativo", True)
        .order("tabela_base")
        .order("regime")
        .order("faixa_inicial")
        .execute()
    )

    return resposta.data or []


def localizar_preco_base(
    precos,
    tabela_base,
    regime,
    faturamento,
):
    candidatos = [
        registro
        for registro in precos
        if texto_limpo(
            registro.get("tabela_base")
        ).lower()
        == texto_limpo(tabela_base).lower()
        and texto_limpo(
            registro.get("regime")
        ).lower()
        == texto_limpo(regime).lower()
        and registro.get("ativo") is not False
    ]

    for registro in candidatos:
        inicio = float(
            registro.get("faixa_inicial") or 0
        )

        sem_limite = bool(
            registro.get("sem_limite_superior")
        )

        final = registro.get("faixa_final")

        dentro_inicio = faturamento >= inicio

        dentro_final = (
            sem_limite
            or final is None
            or faturamento <= float(final)
        )

        if dentro_inicio and dentro_final:
            return registro

    return None


def obter_nome_pergunta(pergunta):
    for campo in [
        "pergunta",
        "texto",
        "descricao",
        "nome",
        "titulo",
    ]:
        valor = texto_limpo(
            pergunta.get(campo)
        )

        if valor:
            return valor

    return f"Pergunta {pergunta.get('id', '')}"


def obter_tipo_pergunta(pergunta):
    for campo in [
        "tipo_resposta",
        "tipo",
        "formato",
        "formato_resposta",
    ]:
        valor = texto_limpo(
            pergunta.get(campo)
        ).lower()

        if valor:
            return valor

    return "texto"


def obter_opcoes(pergunta):
    for campo in [
        "opcoes",
        "opcoes_resposta",
        "alternativas",
    ]:
        valor = pergunta.get(campo)

        if not valor:
            continue

        if isinstance(valor, list):
            return [
                texto_limpo(item)
                for item in valor
                if texto_limpo(item)
            ]

        if isinstance(valor, dict):
            return [
                texto_limpo(item)
                for item in valor.values()
                if texto_limpo(item)
            ]

        texto = texto_limpo(valor)

        if not texto:
            continue

        try:
            carregado = json.loads(texto)

            if isinstance(carregado, list):
                return [
                    texto_limpo(item)
                    for item in carregado
                    if texto_limpo(item)
                ]
        except Exception:
            pass

        separador = (
            "|"
            if "|" in texto
            else ";"
            if ";" in texto
            else ","
        )

        return [
            item.strip()
            for item in texto.split(separador)
            if item.strip()
        ]

    return []


def renderizar_campo_resposta(
    pergunta,
    prefixo,
):
    nome = obter_nome_pergunta(
        pergunta
    )

    tipo = obter_tipo_pergunta(
        pergunta
    )

    opcoes = obter_opcoes(
        pergunta
    )

    chave = (
        f"{prefixo}_"
        f"{pergunta.get('id', nome)}"
    )

    tipo_normalizado = (
        tipo
        .replace("_", " ")
        .replace("-", " ")
    )

    if (
        "sim" in tipo_normalizado
        and "não" in tipo_normalizado
    ) or (
        "sim" in tipo_normalizado
        and "nao" in tipo_normalizado
    ):
        return st.radio(
            nome,
            ["Sim", "Não"],
            horizontal=True,
            key=chave,
        )

    if tipo_normalizado in {
        "boolean",
        "booleano",
        "sim nao",
        "sim não",
    }:
        return st.radio(
            nome,
            ["Sim", "Não"],
            horizontal=True,
            key=chave,
        )

    if opcoes:
        return st.selectbox(
            nome,
            opcoes,
            key=chave,
        )

    if any(
        termo in tipo_normalizado
        for termo in [
            "numero",
            "número",
            "quantidade",
            "inteiro",
            "decimal",
            "valor",
        ]
    ):
        return st.number_input(
            nome,
            min_value=0.0,
            step=1.0,
            value=0.0,
            key=chave,
        )

    if any(
        termo in tipo_normalizado
        for termo in [
            "texto longo",
            "textarea",
            "paragrafo",
            "parágrafo",
        ]
    ):
        return st.text_area(
            nome,
            key=chave,
        )

    return st.text_input(
        nome,
        key=chave,
    )


def montar_detalhamento(detalhamento):
    linhas = []

    for item in detalhamento:
        linhas.append({
            "Regra ID": item.get(
                "regra_id"
            ),
            "Pergunta": item.get(
                "pergunta"
            ),
            "Resposta": item.get(
                "resposta"
            ),
            "Tipo": item.get(
                "tipo"
            ),
            "Acréscimo": item.get(
                "valor"
            ),
        })

    return pd.DataFrame(linhas)


def renderizar_aba_simulador(
    supabase,
):
    st.subheader(
        "Simulador de Precificação"
    )

    st.info(
        "Teste a formação do preço sem criar "
        "lead, proposta ou registro comercial."
    )

    try:
        segmentos = (
            carregar_segmentos_simulador(
                supabase
            )
        )

        precos_base = (
            carregar_precos_base(
                supabase
            )
        )

        mapa_segmentos = (
            carregar_mapa_segmentos_simulador(
                supabase
            )
        )

        regras_todas = (
            get_regras_precificacao()
        )

    except Exception as erro:
        st.error(
            "Não foi possível carregar os "
            f"dados do simulador: {erro}"
        )
        return

    if not segmentos:
        st.warning(
            "Nenhum segmento foi encontrado "
            "em regras_segmento."
        )
        return

    opcoes_segmentos = {}

    for registro in segmentos:
        nome = texto_limpo(
            registro.get("segmentos")
        )

        if nome:
            opcoes_segmentos[nome] = (
                registro
            )

    segmento_escolhido = (
        st.selectbox(
            "Segmento",
            list(
                opcoes_segmentos.keys()
            ),
            key=(
                "simulador_segmento"
            ),
        )
    )

    configuracao_segmento = (
        opcoes_segmentos[
            segmento_escolhido
        ]
    )

    origem_perguntas = (
        texto_limpo(
            configuracao_segmento.get(
                "origem_perguntas"
            )
        )
        or segmento_escolhido
    )

    tabela_base = None

    for item_mapa in mapa_segmentos:
        segmento_mapa = texto_limpo(
            item_mapa.get(
                "segmento_questionario"
            )
        )

        if (
            segmento_mapa.lower()
            == segmento_escolhido.lower()
        ):
            tabela_base = texto_limpo(
                item_mapa.get(
                    "tabela_base"
                )
            )
            break

    if not tabela_base:
        st.warning(
            "Não foi encontrado o vínculo entre o segmento "
            "selecionado e a tabela de preços base."
        )
        return

    regimes_disponiveis = sorted({
        texto_limpo(
            registro.get("regime")
        )
        for registro in precos_base
        if texto_limpo(
            registro.get("tabela_base")
        ).lower()
        == tabela_base.lower()
        and texto_limpo(
            registro.get("regime")
        )
    })

    if not regimes_disponiveis:
        st.warning(
            "Não existem preços base ativos "
            "para a tabela e o segmento selecionados."
        )
        return

    coluna1, coluna2 = st.columns(2)

    with coluna1:
        regime = st.selectbox(
            "Regime tributário",
            regimes_disponiveis,
            key="simulador_regime",
        )

    with coluna2:
        faturamento = st.number_input(
            "Faturamento médio mensal (R$)",
            min_value=0.0,
            step=1000.0,
            format="%.2f",
            key="simulador_faturamento",
        )

    preco_encontrado = (
        localizar_preco_base(
            precos=precos_base,
            tabela_base=tabela_base,
            regime=regime,
            faturamento=float(
                faturamento
            ),
        )
    )

    if preco_encontrado:
        st.success(
            "Preço base encontrado: "
            f"{formatar_moeda(preco_encontrado.get('valor_base'))}"
        )
    else:
        st.warning(
            "Nenhuma faixa de preço base atende "
            "ao faturamento informado."
        )

    try:
        perguntas = (
            get_perguntas_por_origem(
                origem_perguntas
            )
        )
    except Exception as erro:
        st.error(
            "Não foi possível carregar as "
            f"perguntas do segmento: {erro}"
        )
        return

    regras_segmento = [
        regra
        for regra in regras_todas
        if texto_limpo(
            regra.get("segmento_origem")
        ).lower()
        == origem_perguntas.lower()
        and regra.get("ativo") is not False
    ]

    st.divider()
    st.markdown(
        "### Questionário da simulação"
    )

    respostas = {}

    with st.form(
        "form_simulador_precificacao"
    ):
        if perguntas:
            for pergunta in perguntas:
                nome = obter_nome_pergunta(
                    pergunta
                )

                respostas[nome] = (
                    renderizar_campo_resposta(
                        pergunta=pergunta,
                        prefixo="simulador",
                    )
                )
        else:
            st.info(
                "O segmento não possui perguntas "
                "cadastradas."
            )

        calcular = (
            st.form_submit_button(
                "Calcular simulação",
                type="primary",
                use_container_width=True,
            )
        )

    if calcular:
        if not preco_encontrado:
            st.error(
                "Não é possível calcular porque "
                "nenhum preço base foi encontrado."
            )
            return

        try:
            preco_base_inicial = float(
                preco_encontrado.get(
                    "valor_base"
                )
                or 0
            )

            (
                preco_calculado,
                total_acrescimos,
                detalhamento,
            ) = calcular_preco_completo(
                valor_base=(
                    preco_base_inicial
                ),
                respostas_formulario=(
                    respostas
                ),
                regras=regras_segmento,
                segmento=(
                    segmento_escolhido
                ),
            )

            bronze = float(
                preco_calculado
            )

            prata = bronze * 1.15
            ouro = bronze * 1.35

            st.session_state[
                "resultado_simulador_precificacao"
            ] = {
                "segmento": (
                    segmento_escolhido
                ),
                "origem_perguntas": (
                    origem_perguntas
                ),
                "tabela_base": (
                    tabela_base
                ),
                "regime": regime,
                "faturamento": (
                    float(faturamento)
                ),
                "preco_base": (
                    preco_base_inicial
                ),
                "acrescimos": (
                    float(
                        total_acrescimos
                    )
                ),
                "preco_calculado": (
                    float(
                        preco_calculado
                    )
                ),
                "bronze": bronze,
                "prata": prata,
                "ouro": ouro,
                "detalhamento": (
                    detalhamento
                ),
            }

        except Exception as erro:
            st.error(
                "Erro ao calcular a simulação: "
                f"{erro}"
            )
            return

    resultado = st.session_state.get(
        "resultado_simulador_precificacao"
    )

    if not resultado:
        return

    st.divider()
    st.markdown(
        "## Resultado da simulação"
    )

    resumo1, resumo2, resumo3 = (
        st.columns(3)
    )

    resumo1.metric(
        "Preço base inicial",
        formatar_moeda(
            resultado["preco_base"]
        ),
    )

    resumo2.metric(
        "Total de acréscimos",
        formatar_moeda(
            resultado["acrescimos"]
        ),
    )

    resumo3.metric(
        "Preço calculado",
        formatar_moeda(
            resultado["preco_calculado"]
        ),
    )

    plano1, plano2, plano3 = (
        st.columns(3)
    )

    plano1.metric(
        "Bronze",
        formatar_moeda(
            resultado["bronze"]
        ),
    )

    plano2.metric(
        "Prata",
        formatar_moeda(
            resultado["prata"]
        ),
    )

    plano3.metric(
        "Ouro",
        formatar_moeda(
            resultado["ouro"]
        ),
    )

    st.markdown(
        "### Memória de cálculo"
    )

    detalhamento = resultado.get(
        "detalhamento",
        [],
    )

    if detalhamento:
        st.dataframe(
            montar_detalhamento(
                detalhamento
            ),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Acréscimo": (
                    st.column_config.NumberColumn(
                        "Acréscimo",
                        format="R$ %.2f",
                    )
                ),
            },
        )
    else:
        st.info(
            "Nenhum acréscimo foi aplicado."
        )

    st.caption(
        "Esta simulação não criou proposta, lead "
        "ou histórico comercial."
    )
    )
