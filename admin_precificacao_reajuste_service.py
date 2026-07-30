from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


CAMPOS_REGRAS_FIXAS = [
    ("valor_fixo", "Valor fixo"),
]


def converter_decimal(valor):
    """
    Converte valores vindos do Supabase para Decimal.
    Retorna Decimal('0') quando o conteúdo não for numérico.
    """
    if valor is None or valor == "":
        return Decimal("0")

    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def arredondar_valor(valor, regra):
    """
    Aplica a regra de arredondamento escolhida na tela.
    """
    valor = converter_decimal(valor)

    if regra == "Múltiplo de R$ 1,00":
        return valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    if regra == "Múltiplo de R$ 5,00":
        return (
            (valor / Decimal("5"))
            .quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            * Decimal("5")
        )

    if regra == "Múltiplo de R$ 10,00":
        return (
            (valor / Decimal("10"))
            .quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            * Decimal("10")
        )

    if regra == "Finalizar em ,90":
        inteiro = valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        if inteiro > valor:
            inteiro -= Decimal("1")

        candidato = inteiro + Decimal("0.90")

        if candidato < valor:
            candidato += Decimal("1")

        return candidato.quantize(Decimal("0.01"))

    if regra == "Finalizar em ,99":
        inteiro = valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        if inteiro > valor:
            inteiro -= Decimal("1")

        candidato = inteiro + Decimal("0.99")

        if candidato < valor:
            candidato += Decimal("1")

        return candidato.quantize(Decimal("0.01"))

    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_novo_valor(valor_atual, tipo_reajuste, valor_reajuste, arredondamento):
    """
    Calcula o novo valor sem alterar nenhum registro no banco.
    """
    atual = converter_decimal(valor_atual)
    reajuste = converter_decimal(valor_reajuste)

    if tipo_reajuste == "Percentual":
        novo = atual * (Decimal("1") + reajuste / Decimal("100"))
    else:
        novo = atual + reajuste

    if novo < Decimal("0"):
        novo = Decimal("0")

    return arredondar_valor(novo, arredondamento)


def buscar_registros(supabase, tabela):
    resposta = (
        supabase
        .table(tabela)
        .select("*")
        .execute()
    )

    return resposta.data or []


def carregar_mapa_segmentos(supabase):
    """
    Retorna:
    - mapa de segmento do questionário para tabela base;
    - mapa inverso de tabela base para segmentos.
    """
    try:
        registros = buscar_registros(
            supabase,
            "mapa_segmento_precificacao",
        )
    except Exception:
        return {}, {}

    segmento_para_tabela = {}
    tabela_para_segmentos = {}

    for registro in registros:
        if registro.get("ativo") is False:
            continue

        segmento = str(
            registro.get("segmento_questionario") or ""
        ).strip()

        tabela_base = str(
            registro.get("tabela_base") or ""
        ).strip()

        if not segmento or not tabela_base:
            continue

        segmento_para_tabela[segmento] = tabela_base
        tabela_para_segmentos.setdefault(
            tabela_base,
            [],
        ).append(segmento)

    return segmento_para_tabela, tabela_para_segmentos


def segmento_permitido(segmento, configuracao):
    if configuracao.get("todos_segmentos"):
        return True

    selecionados = {
        str(item).strip()
        for item in configuracao.get("segmentos", [])
        if str(item).strip()
    }

    return str(segmento or "").strip() in selecionados


def tabelas_base_permitidas(segmento_para_tabela, configuracao):
    if configuracao.get("todos_segmentos"):
        return None

    selecionados = configuracao.get("segmentos", [])

    return {
        segmento_para_tabela.get(segmento)
        for segmento in selecionados
        if segmento_para_tabela.get(segmento)
    }


def formatar_faixa(registro):
    inicio = registro.get("faixa_inicial")
    final = registro.get("faixa_final")
    sem_limite = bool(registro.get("sem_limite_superior"))

    if sem_limite:
        return f"A partir de {inicio}"

    return f"{inicio} até {final}"


def formatar_faixa_dinamica(registro):
    inicio = registro.get("quantidade_inicial")
    final = registro.get("quantidade_final")

    if final is None:
        return f"{inicio} ou mais"

    return f"{inicio} até {final}"


def adicionar_item(
    itens,
    tabela,
    registro_id,
    campo,
    tipo,
    segmento,
    descricao,
    valor_atual,
    configuracao,
):
    atual = converter_decimal(valor_atual)

    novo = calcular_novo_valor(
        valor_atual=atual,
        tipo_reajuste=configuracao["tipo"],
        valor_reajuste=configuracao["valor"],
        arredondamento=configuracao["arredondamento"],
    )

    diferenca = novo - atual

    itens.append({
        "tabela": tabela,
        "registro_id": registro_id,
        "campo": campo,
        "tipo": tipo,
        "segmento": segmento or "-",
        "descricao": descricao,
        "valor_atual": float(atual),
        "valor_novo": float(novo),
        "diferenca": float(diferenca),
        "alterado": novo != atual,
    })


def gerar_previa_precos_base(
    supabase,
    configuracao,
    segmento_para_tabela,
    tabela_para_segmentos,
):
    registros = buscar_registros(
        supabase,
        "precos_base_precificacao",
    )

    permitidas = tabelas_base_permitidas(
        segmento_para_tabela,
        configuracao,
    )

    itens = []

    for registro in registros:
        if registro.get("ativo") is False:
            continue

        tabela_base = str(
            registro.get("tabela_base") or ""
        ).strip()

        if permitidas is not None and tabela_base not in permitidas:
            continue

        segmentos = tabela_para_segmentos.get(
            tabela_base,
            [],
        )

        segmento_exibicao = (
            ", ".join(segmentos)
            if segmentos
            else tabela_base
        )

        descricao = (
            f"{registro.get('regime') or '-'} | "
            f"{formatar_faixa(registro)}"
        )

        adicionar_item(
            itens=itens,
            tabela="precos_base_precificacao",
            registro_id=registro.get("id"),
            campo="valor_base",
            tipo="Preço Base",
            segmento=segmento_exibicao,
            descricao=descricao,
            valor_atual=registro.get("valor_base"),
            configuracao=configuracao,
        )

    return itens


def gerar_previa_regras(
    regras,
    configuracao,
):
    itens = []

    for regra in regras:
        if regra.get("ativo") is False:
            continue

        segmento = str(
            regra.get("segmento_origem") or ""
        ).strip()

        if not segmento_permitido(segmento, configuracao):
            continue

        tipo_calculo = str(
            regra.get("tipo_calculo") or ""
        ).strip().lower()

        if tipo_calculo != "fixo":
            continue

        for campo, nome_campo in CAMPOS_REGRAS_FIXAS:
            valor = converter_decimal(regra.get(campo))

            if valor <= Decimal("0"):
                continue

            descricao = (
                f"{regra.get('pergunta') or 'Regra sem descrição'} "
                f"| {nome_campo}"
            )

            adicionar_item(
                itens=itens,
                tabela="regras_perguntas_precificacao",
                registro_id=regra.get("id"),
                campo=campo,
                tipo="Regra de valor fixo",
                segmento=segmento,
                descricao=descricao,
                valor_atual=valor,
                configuracao=configuracao,
            )

    return itens


def gerar_previa_faixas(
    supabase,
    regras,
    configuracao,
):
    regras_por_id = {
        int(regra["id"]): regra
        for regra in regras
        if regra.get("id") is not None
    }

    registros = buscar_registros(
        supabase,
        "faixas_precificacao",
    )

    itens = []

    for registro in registros:
        if registro.get("ativo") is False:
            continue

        regra_id = registro.get("regra_pergunta_id")

        try:
            regra_id = int(regra_id)
        except (TypeError, ValueError):
            continue

        regra = regras_por_id.get(regra_id)

        if not regra:
            continue

        segmento = str(
            regra.get("segmento_origem") or ""
        ).strip()

        if not segmento_permitido(segmento, configuracao):
            continue

        descricao = (
            f"{regra.get('pergunta') or 'Regra sem descrição'} "
            f"| Faixa {formatar_faixa_dinamica(registro)}"
        )

        adicionar_item(
            itens=itens,
            tabela="faixas_precificacao",
            registro_id=registro.get("id"),
            campo="valor",
            tipo="Faixa",
            segmento=segmento,
            descricao=descricao,
            valor_atual=registro.get("valor"),
            configuracao=configuracao,
        )

    return itens


def gerar_previa_reajuste(supabase, configuracao):
    """
    Monta uma prévia única para preços base, faixas e regras fixas.

    Esta função somente consulta o Supabase e calcula os novos
    valores em memória. Nenhum update ou insert é executado.
    """
    itens = []
    avisos = []

    segmento_para_tabela, tabela_para_segmentos = (
        carregar_mapa_segmentos(supabase)
    )

    regras = buscar_registros(
        supabase,
        "regras_perguntas_precificacao",
    )

    if configuracao.get("aplicar_precos_base"):
        itens.extend(
            gerar_previa_precos_base(
                supabase=supabase,
                configuracao=configuracao,
                segmento_para_tabela=segmento_para_tabela,
                tabela_para_segmentos=tabela_para_segmentos,
            )
        )

        if (
            not configuracao.get("todos_segmentos")
            and not segmento_para_tabela
        ):
            avisos.append(
                "Não foi possível carregar o mapa entre segmentos "
                "e tabelas de preços base."
            )

    if configuracao.get("aplicar_faixas"):
        itens.extend(
            gerar_previa_faixas(
                supabase=supabase,
                regras=regras,
                configuracao=configuracao,
            )
        )

    if configuracao.get("aplicar_regras_valor_fixo"):
        itens.extend(
            gerar_previa_regras(
                regras=regras,
                configuracao=configuracao,
            )
        )

    total_encontrados = len(itens)
    total_alterados = sum(
        1 for item in itens if item["alterado"]
    )
    total_iguais = total_encontrados - total_alterados

    total_antes = sum(
        converter_decimal(item["valor_atual"])
        for item in itens
    )

    total_depois = sum(
        converter_decimal(item["valor_novo"])
        for item in itens
    )

    return {
        "itens": itens,
        "resumo": {
            "total_encontrados": total_encontrados,
            "total_alterados": total_alterados,
            "total_iguais": total_iguais,
            "total_antes": float(total_antes),
            "total_depois": float(total_depois),
            "diferenca_total": float(total_depois - total_antes),
        },
        "avisos": avisos,
    }
