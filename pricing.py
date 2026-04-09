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


def calcular_precificacao_completa(regime_sel, qtd_func, qtd_notas, qtd_lanca, possui_filial, total_pergunta_segmento):
    custo_hora = calcular_custo_hora_real()
    total_horas_est = calcular_horas_estimadas(regime_sel, qtd_func, qtd_notas, qtd_lanca, possui_filial)

    perc_imposto = get_config_val("impostos_faturamento") / 100
    custo_operacional = calcular_custo_operacional(total_horas_est, custo_hora, total_pergunta_segmento)

    valores = {
        "bronze": calcular_venda(custo_operacional, perc_imposto, 20),
        "prata": calcular_venda(custo_operacional, perc_imposto, 35),
        "ouro": calcular_venda(custo_operacional, perc_imposto, 50),
    }

    memoria = {
        "custo_hora": custo_hora,
        "horas_estimadas": total_horas_est,
        "perc_imposto": perc_imposto,
        "custo_operacional": custo_operacional,
        "adicional_segmento": total_pergunta_segmento,
        "possui_filial": possui_filial,
        "qtd_func": qtd_func,
        "qtd_notas": qtd_notas,
        "qtd_lanca": qtd_lanca,
        "regime": regime_sel,
    }

    return valores, memoria
