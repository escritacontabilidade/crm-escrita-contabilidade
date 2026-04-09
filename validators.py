def validar_campos_basicos_cliente(nome_cliente, regime_sel, seg_sel):
    erros = []

    if not nome_cliente or not str(nome_cliente).strip():
        erros.append("Informe o nome da empresa.")

    if not regime_sel or not str(regime_sel).strip():
        erros.append("Informe o regime tributário.")

    if not seg_sel or not str(seg_sel).strip():
        erros.append("Selecione o segmento.")

    return erros


def validar_formulario_lead(nome_empresa, responsavel, whatsapp, segmento):
    erros = []

    if not nome_empresa or not str(nome_empresa).strip():
        erros.append("Informe o nome da empresa.")

    if not responsavel or not str(responsavel).strip():
        erros.append("Informe o nome do responsável.")

    if not whatsapp or not str(whatsapp).strip():
        erros.append("Informe o WhatsApp.")

    if not segmento or not str(segmento).strip():
        erros.append("Selecione o segmento.")

    return erros


def validar_pergunta_segmento(tipo_campo, pergunta, opcoes, pesos):
    erros = []

    if not pergunta or not str(pergunta).strip():
        erros.append("A pergunta não pode ficar vazia.")

    if tipo_campo == "Múltipla Escolha":
        lista_opcoes = [o.strip() for o in str(opcoes).split(",") if o.strip()]
        lista_pesos = [p.strip() for p in str(pesos).split(",") if p.strip()]

        if not lista_opcoes:
            erros.append("Informe ao menos uma opção.")

        if not lista_pesos:
            erros.append("Informe os pesos das opções.")

        if len(lista_opcoes) != len(lista_pesos):
            erros.append("A quantidade de opções deve ser igual à quantidade de pesos.")

        for peso in lista_pesos:
            try:
                float(peso.replace(",", "."))
            except ValueError:
                erros.append(f"Peso inválido: {peso}")

    elif tipo_campo == "Número (Multiplicador)":
        try:
            float(str(pesos).replace(",", "."))
        except ValueError:
            erros.append("Para pergunta numérica, informe um peso numérico válido.")

    return erros
