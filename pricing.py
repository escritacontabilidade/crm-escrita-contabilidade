from database import get_config_val, get_peso_esforco


def calcular_custo_hora_real():
    folha = get_config_val("total_folha")
    fixas = get_config_val("despesas_fixas")
    horas = get_config_val("horas_uteis_mes")
    equipe = get_config_val("num_colaboradores")

    custo_total = folha + fixas
    capacidade_horas = horas * equipe

    if capacidade_horas <= 0:
        raise ValueError("Capacidade de horas inválida. Verifique horas úteis e número de colaboradores.")

    return custo_total / capacidade_horas


def calcular_horas_estimadas(regime_sel, qtd_func, qtd_notas, qtd_lanca, possui_filial):
    h_base = get_peso_esforco(regime_sel, "Base")
    p_func = get_peso_esforco(regime_sel, "Funcionario")
    p_nota = get_peso_esforco(regime_sel, "Nota Fiscal")
    p_lanc = get_peso_esforco(regime_sel, "Lancamento")
    h_filial = get_peso_esforco("Filial", "Adicional Base") if possui_filial else 0

    total_horas_est = h_base + h_filial + (qtd_func * p_func) + (qtd_notas * p_nota) + (qtd_lanca * p_lanc)
    return total_horas_est


def calcular_custo_operacional(total_horas_est, custo_hora, total_pergunta_segmento):
    return (total_horas_est * custo_hora) + total_pergunta_segmento


def calcular_venda(custo_operacional, perc_imposto, margem):
    margem_decimal = margem / 100
    divisor = 1 - perc_imposto - margem_decimal

    if divisor <= 0:
        raise ValueError(
            f"Divisor inválido no cálculo de venda. Imposto={perc_imposto:.2%}, margem={margem_decimal:.2%}"
        )

    return custo_operacional / divisor


def calcular_adicionais(respostas, regras, valor_base):
    total = 0

    for r in regras:
        pergunta_id = r["pergunta_id"]
        resposta = respostas.get(pergunta_id)

        if resposta is None:
            continue

        tipo = r["tipo_regra"]  # fixo, faixa, percentual
        valor = r["valor"]

        # REGRA FIXA
        if tipo == "fixo":
            if str(resposta).lower() == "sim":
                total += float(valor)

        # REGRA POR FAIXA
        elif tipo == "faixa":
            try:
                resposta_int = int(resposta)
            except:
                continue

            if r["faixa_inicio"] <= resposta_int <= r["faixa_fim"]:
                total += float(valor)

        # REGRA PERCENTUAL
        elif tipo == "percentual":
            if str(resposta).lower() == "sim":
                total += valor_base * float(valor)

    return total

def calcular_preco_final(valor_base, respostas, regras):
    adicionais = calcular_adicionais(respostas, regras, valor_base)

    preco_final = valor_base + adicionais

    return preco_final, {
        "valor_base": valor_base,
        "adicionais": adicionais,
        "preco_final": preco_final
    }
