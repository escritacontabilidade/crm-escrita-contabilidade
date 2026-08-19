import streamlit as st


VALOR_FILIAL_SEM_MOVIMENTO = 300.00
VALOR_FILIAL_COM_MOVIMENTO = 500.00

CHAVE_DETALHAMENTO_FILIAIS = "Detalhamento das filiais"


def eh_pergunta_filial(pergunta):
    """
    Identifica a pergunta padrão de existência de filial.
    """
    texto = str(pergunta or "").strip().lower()
    texto = texto.lstrip("-").strip()

    return texto == "a empresa possui filial?"


def calcular_adicional_filiais(filiais):
    """
    Soma apenas as filiais cuja contabilidade ficará
    sob responsabilidade da Escrita.
    """
    total = 0.0

    for filial in filiais or []:
        responsabilidade = str(
            filial.get("responsabilidade_escrita") or ""
        ).strip()

        movimento = str(
            filial.get("possui_movimento") or ""
        ).strip()

        if responsabilidade != "Sim":
            continue

        if movimento == "Sim":
            total += VALOR_FILIAL_COM_MOVIMENTO
        else:
            total += VALOR_FILIAL_SEM_MOVIMENTO

    return float(total)


def renderizar_detalhes_filiais(
    resposta_possui_filial,
    prefixo,
    respostas_iniciais=None,
):
    """
    Renderiza a estrutura dinâmica das filiais.

    Retorna:
        {
            "quantidade_filiais": int,
            "filiais": [...],
            "adicional_total": float
        }
    """

    if str(resposta_possui_filial or "").strip() != "Sim":
        return {
            "quantidade_filiais": 0,
            "filiais": [],
            "adicional_total": 0.0,
        }

    respostas_iniciais = (
        respostas_iniciais
        if isinstance(respostas_iniciais, dict)
        else {}
    )

    quantidade_inicial = respostas_iniciais.get(
        "quantidade_filiais",
        1,
    )

    try:
        quantidade_inicial = int(quantidade_inicial or 1)
    except Exception:
        quantidade_inicial = 1

    quantidade_inicial = max(1, quantidade_inicial)

    st.markdown("##### Detalhamento das filiais")

    quantidade_filiais = st.number_input(
        "Quantas filiais a empresa possui?",
        min_value=1,
        step=1,
        value=quantidade_inicial,
        key=f"{prefixo}_quantidade_filiais",
    )

    filiais_iniciais = respostas_iniciais.get("filiais", [])

    if not isinstance(filiais_iniciais, list):
        filiais_iniciais = []

    filiais = []

    for indice in range(int(quantidade_filiais)):
        numero_filial = indice + 1

        inicial = (
            filiais_iniciais[indice]
            if (
                indice < len(filiais_iniciais)
                and isinstance(filiais_iniciais[indice], dict)
            )
            else {}
        )

        movimento_inicial = str(
            inicial.get("possui_movimento") or "Não"
        ).strip()

        if movimento_inicial not in ["Sim", "Não"]:
            movimento_inicial = "Não"

        responsabilidade_inicial = str(
            inicial.get("responsabilidade_escrita") or "Não"
        ).strip()

        if responsabilidade_inicial not in ["Sim", "Não"]:
            responsabilidade_inicial = "Não"

        with st.container(border=True):
            st.markdown(f"**Filial {numero_filial}**")

            col1, col2 = st.columns(2)

            with col1:
                possui_movimento = st.radio(
                    "Possui movimento?",
                    ["Sim", "Não"],
                    index=0 if movimento_inicial == "Sim" else 1,
                    horizontal=True,
                    key=(
                        f"{prefixo}_filial_"
                        f"{numero_filial}_movimento"
                    ),
                )

            with col2:
                responsabilidade_escrita = st.radio(
                    "A Escrita será responsável pela "
                    "contabilidade desta filial?",
                    ["Sim", "Não"],
                    index=(
                        0
                        if responsabilidade_inicial == "Sim"
                        else 1
                    ),
                    horizontal=True,
                    key=(
                        f"{prefixo}_filial_"
                        f"{numero_filial}_responsabilidade"
                    ),
                )

        adicional_filial = 0.0

        if responsabilidade_escrita == "Sim":
            adicional_filial = (
                VALOR_FILIAL_COM_MOVIMENTO
                if possui_movimento == "Sim"
                else VALOR_FILIAL_SEM_MOVIMENTO
            )

        filiais.append({
            "numero": numero_filial,
            "possui_movimento": possui_movimento,
            "responsabilidade_escrita": responsabilidade_escrita,
            "adicional": float(adicional_filial),
        })

    adicional_total = calcular_adicional_filiais(filiais)

    return {
        "quantidade_filiais": int(quantidade_filiais),
        "filiais": filiais,
        "adicional_total": float(adicional_total),
    }
