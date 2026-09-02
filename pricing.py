from database import (
    get_config_val,
    get_peso_esforco,
    get_faixas_precificacao,
)


def calcular_custo_hora_real():
    folha = get_config_val("total_folha")
    fixas = get_config_val("despesas_fixas")
    horas = get_config_val("horas_uteis_mes")
    equipe = get_config_val("num_colaboradores")

    custo_total = folha + fixas
    capacidade_horas = horas * equipe

    if capacidade_horas <= 0:
        raise ValueError(
            "Capacidade de horas inválida. "
            "Verifique horas úteis e número de colaboradores."
        )

    return custo_total / capacidade_horas


def calcular_horas_estimadas(
    regime_sel,
    qtd_func,
    qtd_notas,
    qtd_lanca,
    possui_filial
):
    h_base = get_peso_esforco(regime_sel, "Base")
    p_func = get_peso_esforco(regime_sel, "Funcionario")
    p_nota = get_peso_esforco(regime_sel, "Nota Fiscal")
    p_lanc = get_peso_esforco(regime_sel, "Lancamento")

    h_filial = (
        get_peso_esforco("Filial", "Adicional Base")
        if possui_filial
        else 0
    )

    total_horas_est = (
        h_base
        + h_filial
        + (qtd_func * p_func)
        + (qtd_notas * p_nota)
        + (qtd_lanca * p_lanc)
    )

    return total_horas_est


def calcular_custo_operacional(
    total_horas_est,
    custo_hora,
    total_pergunta_segmento
):
    return (
        total_horas_est * custo_hora
    ) + total_pergunta_segmento


def calcular_venda(
    custo_operacional,
    perc_imposto,
    margem
):
    margem_decimal = margem / 100

    divisor = (
        1
        - perc_imposto
        - margem_decimal
    )

    if divisor <= 0:
        raise ValueError(
            "Divisor inválido no cálculo de venda. "
            f"Imposto={perc_imposto:.2%}, "
            f"margem={margem_decimal:.2%}"
        )

    return custo_operacional / divisor


def _eh_percentual_base(regra):
    """
    Identifica regras que devem calcular um percentual
    sobre o valor-base.

    A regra deve possuir [PERCENTUAL_BASE] no campo observacao.
    """

    observacao = str(
        regra.get("observacao") or ""
    ).strip().upper()

    return "[PERCENTUAL_BASE]" in observacao


def _calcular_percentual_base(
    regra,
    valor_base
):
    """
    Para regras marcadas com [PERCENTUAL_BASE],
    valor_unitario deve ser armazenado em decimal.

    Exemplo:
    10% = 0.10
    """

    try:
        percentual = float(
            regra.get("valor_unitario") or 0
        )
    except (TypeError, ValueError):
        percentual = 0.0

    if percentual <= 0:
        return 0.0

    return float(valor_base or 0) * percentual


def calcular_adicionais(
    respostas,
    regras,
    valor_base
):
    total = 0.0

    for r in regras:
        pergunta = r.get("pergunta")

        if not pergunta:
            continue

        resposta = respostas.get(pergunta)

        if resposta is None:
            continue

        tipo = str(
            r.get("tipo_calculo") or ""
        ).strip()

        if not tipo:
            continue

        modo = str(
            r.get("modo_aplicacao") or ""
        ).strip()

        resposta_gatilho = str(
            r.get("resposta_gatilho") or ""
        ).strip()

        resposta_str = str(
            resposta
        ).strip()

        # -------------------------------------------------
        # VERIFICAÇÃO DO GATILHO
        # -------------------------------------------------

        if modo == "resposta_igual":
            if (
                resposta_str.lower()
                != resposta_gatilho.lower()
            ):
                continue

        elif modo == "quantidade_maior_que_zero":
            try:
                quantidade = float(resposta)
            except (TypeError, ValueError):
                continue

            if quantidade <= 0:
                continue

        elif modo == "resposta_preenchida":
            if resposta_str == "":
                continue

        # -------------------------------------------------
        # PERCENTUAL SOBRE VALOR-BASE
        # -------------------------------------------------

        if _eh_percentual_base(r):
            total += _calcular_percentual_base(
                r,
                valor_base
            )

            continue

        # -------------------------------------------------
        # FIXO
        # -------------------------------------------------

        if tipo == "fixo":
            total += float(
                r.get("valor_fixo") or 0
            )

        # -------------------------------------------------
        # POR QUANTIDADE
        # -------------------------------------------------

        elif tipo == "por_quantidade":
            try:
                qtd = float(resposta)
            except (TypeError, ValueError):
                continue

            if qtd > 0:
                total += (
                    qtd
                    * float(
                        r.get("valor_unitario") or 0
                    )
                )

        # -------------------------------------------------
        # ESCALONADO - MÉTODO LEGADO
        # -------------------------------------------------

        elif tipo == "escalonado":
            try:
                qtd = float(resposta)
            except (TypeError, ValueError):
                continue

            if qtd <= 0:
                continue

            valor_ate_29 = float(
                r.get("valor_ate_29") or 0
            )

            valor_a_partir_30 = float(
                r.get("valor_a_partir_30") or 0
            )

            if qtd <= 29:
                total += (
                    qtd * valor_ate_29
                )
            else:
                total += (
                    qtd * valor_a_partir_30
                )

    return total


def calcular_preco_final(
    valor_base,
    respostas,
    regras
):
    adicionais = calcular_adicionais(
        respostas,
        regras,
        valor_base
    )

    preco_final = (
        valor_base
        + adicionais
    )

    return preco_final, {
        "valor_base": valor_base,
        "adicionais": adicionais,
        "preco_final": preco_final,
    }


def calcular_valor_regra(
    regra,
    resposta,
    faixas_precificacao,
    valor_base=0
):
    tipo = str(
        regra.get("tipo_calculo") or ""
    ).strip()

    modo = str(
        regra.get("modo_aplicacao") or ""
    ).strip()

    resposta_gatilho = str(
        regra.get("resposta_gatilho") or ""
    ).strip()

    if resposta is None:
        return 0.0

    resposta_str = str(
        resposta
    ).strip()

    # =====================================================
    # 1. VERIFICA SE A REGRA DEVE SER APLICADA
    # =====================================================

    if modo == "resposta_igual":
        if (
            resposta_str.lower()
            != resposta_gatilho.lower()
        ):
            return 0.0

    elif modo == "quantidade_maior_que_zero":
        try:
            quantidade = float(resposta)
        except (TypeError, ValueError):
            return 0.0

        if quantidade <= 0:
            return 0.0

    elif modo == "resposta_preenchida":
        if resposta_str == "":
            return 0.0

    # =====================================================
    # 2. REGRA PERCENTUAL SOBRE O VALOR-BASE
    # =====================================================

    if _eh_percentual_base(regra):
        return _calcular_percentual_base(
            regra,
            valor_base
        )

    # =====================================================
    # 3. REGRA COM VALOR FIXO
    # =====================================================

    if tipo == "fixo":
        return float(
            regra.get("valor_fixo") or 0
        )

    # =====================================================
    # 4. REGRA COM VALOR UNITÁRIO SIMPLES
    # =====================================================

    if tipo == "por_quantidade":
        try:
            quantidade = float(resposta)
        except (TypeError, ValueError):
            return 0.0

        if quantidade <= 0:
            return 0.0

        valor_unitario = float(
            regra.get("valor_unitario") or 0
        )

        return (
            quantidade
            * valor_unitario
        )

    # =====================================================
    # 5. REGRA BASEADA EM FAIXAS DINÂMICAS
    # =====================================================

    if tipo in [
        "escalonado",
        "processos_faixa",
        "faixas"
    ]:
        try:
            quantidade = float(resposta)
        except (TypeError, ValueError):
            return 0.0

        if quantidade <= 0:
            return 0.0

        regra_id = int(
            regra.get("id")
        )

        faixas = faixas_precificacao.get(
            regra_id,
            []
        )

        if not faixas:
            pergunta = str(
                regra.get("pergunta")
                or regra_id
            ).strip()

            raise ValueError(
                f"A regra '{pergunta}' "
                "não possui faixas "
                "de precificação cadastradas."
            )

        for faixa in faixas:
            quantidade_inicial = float(
                faixa.get(
                    "quantidade_inicial"
                ) or 0
            )

            quantidade_final = faixa.get(
                "quantidade_final"
            )

            if quantidade_final is not None:
                quantidade_final = float(
                    quantidade_final
                )

            dentro_do_inicio = (
                quantidade
                >= quantidade_inicial
            )

            dentro_do_final = (
                quantidade_final is None
                or quantidade
                <= quantidade_final
            )

            if (
                dentro_do_inicio
                and dentro_do_final
            ):
                valor_unitario = float(
                    faixa.get("valor") or 0
                )

                return (
                    quantidade
                    * valor_unitario
                )

        pergunta = str(
            regra.get("pergunta")
            or regra_id
        ).strip()

        raise ValueError(
            f"A quantidade {quantidade:g} "
            "não está coberta pelas faixas "
            f"da regra '{pergunta}'."
        )

    return 0.0


def calcular_preco_completo(
    valor_base,
    respostas_formulario,
    regras,
    segmento=None
):
    total_acrescimos = 0.0
    detalhamento = []

    faixas_precificacao = (
        get_faixas_precificacao()
    )

    for regra in regras:
        pergunta = str(
            regra.get("pergunta") or ""
        ).strip()

        if not pergunta:
            continue

        resposta = respostas_formulario.get(
            pergunta
        )

        if resposta is None:
            continue

        valor = calcular_valor_regra(
            regra,
            resposta,
            faixas_precificacao,
            valor_base
        )

        if valor > 0:
            detalhamento.append({
                "regra_id": regra.get("id"),
                "pergunta": pergunta,
                "resposta": resposta,
                "valor": valor,
                "tipo": regra.get(
                    "tipo_calculo"
                ),
            })

            total_acrescimos += valor

    preco_base_calculado = (
        valor_base
        + total_acrescimos
    )

    return (
        preco_base_calculado,
        total_acrescimos,
        detalhamento,
    )
    
