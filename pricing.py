from functools import lru_cache
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
        pergunta = r.get("pergunta")
        if not pergunta:
            continue
        resposta = respostas.get(pergunta)

        if resposta is None:
            continue

        tipo = r.get("tipo_calculo")
        if not tipo:
            continue

        # -------------------------
        # FIXO
        # -------------------------
        if tipo == "fixo":
            gatilho = str(r.get("resposta_gatilho", "")).strip().lower()
            resp = str(resposta).strip().lower()

            if resp == gatilho:
                total += float(r.get("valor_fixo") or 0)

        # -------------------------
        # POR QUANTIDADE
        # -------------------------
        elif tipo == "por_quantidade":
            try:
                qtd = int(resposta)
            except:
                continue

            if qtd > 0:
                total += qtd * float(r.get("valor_unitario") or 0)

        # -------------------------
        # ESCALONADO
        # -------------------------
        elif tipo == "escalonado":
            try:
                qtd = int(resposta)
            except:
                continue

            if qtd <= 29:
                total += qtd * float(r.get("valor_ate_29") or 0)
            else:
                total += qtd * float(r.get("valor_a_partir_30") or 0)

    return total

def calcular_preco_final(valor_base, respostas, regras):
    adicionais = calcular_adicionais(respostas, regras, valor_base)

    preco_final = valor_base + adicionais

    return preco_final, {
        "valor_base": valor_base,
        "adicionais": adicionais,
        "preco_final": preco_final
    }

def calcular_valor_regra(regra, resposta, faixas_precificacao):
    tipo = str(regra.get("tipo_calculo") or "").strip()
    modo = str(regra.get("modo_aplicacao") or "").strip()
    resposta_gatilho = str(regra.get("resposta_gatilho") or "").strip()

    if resposta is None:
        return 0.0

    resposta_str = str(resposta).strip()

    # 1. Verifica se a regra deve ser aplicada
    if modo == "resposta_igual":
        if resposta_str.lower() != resposta_gatilho.lower():
            return 0.0

    elif modo == "quantidade_maior_que_zero":
        try:
            qtd = float(resposta)
            if qtd <= 0:
                return 0.0
        except (TypeError, ValueError):
            return 0.0

    elif modo == "resposta_preenchida":
        if resposta_str == "":
            return 0.0

    # 2. Cálculo fixo
    if tipo == "fixo":
        return float(regra.get("valor_fixo") or 0)

    # 3. Cálculo por quantidade
    if tipo == "por_quantidade":
        try:
            qtd = float(resposta)
        except (TypeError, ValueError):
            return 0.0

        valor_unitario = float(regra.get("valor_unitario") or 0)
        return qtd * valor_unitario

    # 4. Cálculo por faixas dinâmicas
    if tipo in ["escalonado", "processos_faixa", "faixas"]:
        try:
            qtd = float(resposta)
        except (TypeError, ValueError):
            return 0.0

        if qtd <= 0:
            return 0.0

        regra_id = regra.get("id")

        faixas = faixas_precificacao.get(regra_id, [])

      
        for faixa in faixas:
            quantidade_inicial = float(
                faixa.get("quantidade_inicial") or 0
            )

            quantidade_final = faixa.get("quantidade_final")

            if quantidade_final is not None:
                quantidade_final = float(quantidade_final)

            valor_faixa = float(faixa.get("valor") or 0)

            dentro_do_inicio = qtd >= quantidade_inicial

            dentro_do_final = (
                quantidade_final is None
                or qtd <= quantidade_final
            )

            if dentro_do_inicio and dentro_do_final:
                return qtd * valor_faixa

        # Compatibilidade temporária com regras antigas
        if tipo == "escalonado":
            valor_ate_29 = float(regra.get("valor_ate_29") or 0)
            valor_a_partir_30 = float(
                regra.get("valor_a_partir_30") or 0
            )

            if qtd <= 29:
                return qtd * valor_ate_29

            return qtd * valor_a_partir_30

        if tipo == "processos_faixa":
            valor_ate_100 = float(
                regra.get("valor_ate_100") or 0
            )
            valor_101_500 = float(
                regra.get("valor_101_500") or 0
            )
            valor_acima_500 = float(
                regra.get("valor_acima_500") or 0
            )

            if qtd <= 100:
                return qtd * valor_ate_100

            if qtd <= 500:
                return qtd * valor_101_500

            return qtd * valor_acima_500

    return 0.0
        
def calcular_preco_completo(
    valor_base,
    respostas_formulario,
    regras,
    segmento=None
):
    total_acrescimos = 0
    detalhamento = []

    faixas_precificacao = get_faixas_precificacao()

    for regra in regras:
        pergunta = str(regra.get("pergunta") or "").strip()

        if not pergunta:
            continue

        resposta = respostas_formulario.get(pergunta)

        if resposta is None:
            continue

        valor = calcular_valor_regra(
            regra,
            resposta,
            faixas_precificacao
        )

        if valor > 0:
            detalhamento.append({
                "regra_id": regra.get("id"),
                "pergunta": pergunta,
                "resposta": resposta,
                "valor": valor,
                "tipo": regra.get("tipo_calculo"),
            })

            total_acrescimos += valor

    preco_base_calculado = valor_base + total_acrescimos

    return (
        preco_base_calculado,
        total_acrescimos,
        detalhamento,
    )
    
