import streamlit as st

from database import get_supabase


TIPOS_CAMPO_TEXTO = {
    "Texto",
    "Texto Livre",
    "Texto Curto",
}

TIPOS_CAMPO_NUMERO = {
    "Número",
    "Numero",
}

TIPOS_CAMPO_MOEDA = {
    "Moeda",
}

TIPOS_CAMPO_ESCOLHA = {
    "Múltipla Escolha",
    "Multipla Escolha",
    "Seleção",
    "Selecao",
}

TIPOS_CAMPO_ARQUIVO = {
    "Arquivo",
}


def _texto(valor):
    return str(valor or "").strip()


def _chave(prefixo, pergunta_id):
    return f"{prefixo}_{pergunta_id}"


def _carregar_tipos(supabase):
    resultado = (
        supabase
        .table("tipos_constituicao")
        .select(
            "id,nome,descricao,ordem"
        )
        .eq("ativo", True)
        .order("ordem")
        .execute()
    )

    return resultado.data or []


def _carregar_perguntas(
    supabase,
    tipo_constituicao_id,
):
    resultado = (
        supabase
        .table("perguntas_constituicao")
        .select("*")
        .eq(
            "tipo_constituicao_id",
            tipo_constituicao_id,
        )
        .eq("ativo", True)
        .order("ordem")
        .order("id")
        .execute()
    )

    return resultado.data or []


def _opcoes(pergunta):
    valor = pergunta.get("opcoes")

    if not valor:
        return []

    return [
        item.strip()
        for item in str(valor).split(",")
        if item.strip()
    ]


def _campo_obrigatorio(pergunta):
    return bool(
        pergunta.get("obrigatoria")
    )


def _rotulo(pergunta):
    texto = _texto(
        pergunta.get("pergunta")
    )

    if _campo_obrigatorio(pergunta):
        return f"{texto} *"

    return texto


def _renderizar_campo(
    pergunta,
    prefixo,
):
    pergunta_id = pergunta["id"]

    tipo = _texto(
        pergunta.get("tipo_campo")
    )

    rotulo = _rotulo(pergunta)

    observacao = _texto(
        pergunta.get("observacao")
    )

    chave = _chave(
        prefixo,
        pergunta_id,
    )

    if tipo in TIPOS_CAMPO_NUMERO:
        valor = st.number_input(
            rotulo,
            min_value=0,
            step=1,
            value=None,
            key=chave,
            help=observacao or None,
        )

        return valor

    if tipo in TIPOS_CAMPO_MOEDA:
        valor = st.number_input(
            rotulo,
            min_value=0.0,
            step=100.0,
            value=None,
            format="%.2f",
            key=chave,
            help=observacao or None,
        )

        return valor

    if tipo in TIPOS_CAMPO_ESCOLHA:
        opcoes = _opcoes(
            pergunta
        )

        valor = st.selectbox(
            rotulo,
            options=[""] + opcoes,
            index=0,
            key=chave,
            help=observacao or None,
        )

        return valor

    if tipo in TIPOS_CAMPO_ARQUIVO:
        arquivo = st.file_uploader(
            rotulo,
            key=chave,
            help=observacao or None,
            type=[
                "pdf",
                "png",
                "jpg",
                "jpeg",
                "doc",
                "docx",
            ],
        )

        return arquivo

    valor = st.text_area(
        rotulo,
        key=chave,
        help=observacao or None,
    )

    return valor


def _valor_preenchido(
    valor,
    tipo_campo,
):
    if tipo_campo in TIPOS_CAMPO_ARQUIVO:
        return valor is not None

    if tipo_campo in TIPOS_CAMPO_NUMERO:
        return valor is not None

    if tipo_campo in TIPOS_CAMPO_MOEDA:
        return valor is not None

    return bool(
        _texto(valor)
    )


def _validar_obrigatorios(
    perguntas,
    respostas,
    arquivos,
):
    faltantes = []

    for pergunta in perguntas:
        if not _campo_obrigatorio(
            pergunta
        ):
            continue

        pergunta_id = pergunta["id"]

        tipo = _texto(
            pergunta.get("tipo_campo")
        )

        if tipo in TIPOS_CAMPO_ARQUIVO:
            valor = arquivos.get(
                pergunta_id
            )
        else:
            valor = respostas.get(
                str(pergunta_id)
            )

        if not _valor_preenchido(
            valor,
            tipo,
        ):
            faltantes.append(
                _texto(
                    pergunta.get(
                        "pergunta"
                    )
                )
            )

    return faltantes


def _salvar_solicitacao(
    supabase,
    tipo_constituicao_id,
    nome_empresa,
    nome_responsavel,
    email,
    telefone,
    cnpj,
    respostas,
):
    dados = {
        "tipo_constituicao_id": (
            tipo_constituicao_id
        ),
        "nome_empresa": (
            nome_empresa or None
        ),
        "nome_responsavel": (
            nome_responsavel
        ),
        "email": email or None,
        "telefone": telefone or None,
        "cnpj": cnpj or None,
        "respostas": respostas,
        "status": "Novo",
        "ativo": True,
    }

    resultado = (
        supabase
        .table(
            "solicitacoes_constituicao"
        )
        .insert(dados)
        .execute()
    )

    if not resultado.data:
        raise RuntimeError(
            "A solicitação não foi gravada."
        )

    return resultado.data[0]


def _salvar_metadados_arquivos(
    supabase,
    solicitacao_id,
    perguntas,
    arquivos,
):
    """
    Nesta primeira versão, registra os documentos
    informados no formulário.

    O armazenamento físico dos arquivos será
    conectado em etapa própria.
    """

    mapa_perguntas = {
        pergunta["id"]: pergunta
        for pergunta in perguntas
    }

    registros = []

    for pergunta_id, arquivo in (
        arquivos.items()
    ):
        if arquivo is None:
            continue

        pergunta = mapa_perguntas.get(
            pergunta_id,
            {},
        )

        registros.append({
            "solicitacao_id": (
                solicitacao_id
            ),
            "pergunta_id": pergunta_id,
            "tipo_documento": _texto(
                pergunta.get("pergunta")
            ),
            "nome_original": (
                arquivo.name
            ),
            "nome_salvo": None,
            "drive_file_id": None,
            "drive_link": None,
            "mime_type": getattr(
                arquivo,
                "type",
                None,
            ),
        })

    if registros:
        (
            supabase
            .table(
                "solicitacoes_constituicao_arquivos"
            )
            .insert(registros)
            .execute()
        )


def renderizar_formulario_constituicao():
    supabase = get_supabase()

    st.title(
        "Solicitação de Constituição de Empresa"
    )

    st.write(
        "Preencha as informações abaixo para que "
        "a Escrita Contabilidade possa analisar "
        "sua solicitação e preparar a proposta."
    )

    st.caption(
        "Os campos identificados com * são "
        "obrigatórios."
    )

    try:
        tipos = _carregar_tipos(
            supabase
        )
    except Exception as erro:
        st.error(
            "Não foi possível carregar os tipos "
            "de solicitação. "
            f"Detalhes: {erro}"
        )
        return

    if not tipos:
        st.warning(
            "Nenhum tipo de solicitação está "
            "disponível no momento."
        )
        return

    nomes_tipos = [
        item["nome"]
        for item in tipos
    ]

    mapa_tipos = {
        item["nome"]: item
        for item in tipos
    }

    st.subheader(
        "1. Tipo de solicitação"
    )

    tipo_escolhido = st.selectbox(
        "O que você deseja solicitar? *",
        options=[""] + nomes_tipos,
        index=0,
        key="constituicao_tipo",
    )

    if not tipo_escolhido:
        st.info(
            "Selecione o tipo de solicitação "
            "para visualizar o questionário."
        )
        return

    tipo = mapa_tipos[
        tipo_escolhido
    ]

    descricao = _texto(
        tipo.get("descricao")
    )

    if descricao:
        st.caption(
            descricao
        )

    st.divider()

    st.subheader(
        "2. Identificação"
    )

    nome_empresa = st.text_input(
        "Nome da empresa ou razão social pretendida"
    )

    nome_responsavel = st.text_input(
        "Nome do responsável pelo preenchimento *"
    )

    coluna1, coluna2 = st.columns(2)

    with coluna1:
        email = st.text_input(
            "E-mail *"
        )

    with coluna2:
        telefone = st.text_input(
            "Telefone / WhatsApp *"
        )

    cnpj = st.text_input(
        "CNPJ, caso já exista"
    )

    st.divider()

    try:
        perguntas = (
            _carregar_perguntas(
                supabase,
                tipo["id"],
            )
        )
    except Exception as erro:
        st.error(
            "Não foi possível carregar as "
            "perguntas do formulário. "
            f"Detalhes: {erro}"
        )
        return

    if not perguntas:
        st.warning(
            "Não existem perguntas cadastradas "
            "para esta modalidade."
        )
        return

    respostas = {}
    arquivos = {}

    grupo_atual = None

    for pergunta in perguntas:
        grupo = _texto(
            pergunta.get("grupo")
        )

        if grupo != grupo_atual:
            grupo_atual = grupo

            st.subheader(
                grupo_atual
            )

        tipo_campo = _texto(
            pergunta.get(
                "tipo_campo"
            )
        )

        valor = _renderizar_campo(
            pergunta,
            prefixo=(
                f"const_{tipo['id']}"
            ),
        )

        if tipo_campo in (
            TIPOS_CAMPO_ARQUIVO
        ):
            arquivos[
                pergunta["id"]
            ] = valor
        else:
            respostas[
                str(pergunta["id"])
            ] = valor

    st.divider()

    aceite = st.checkbox(
        "Confirmo que as informações fornecidas "
        "são verdadeiras e poderão ser utilizadas "
        "pela Escrita Contabilidade para análise "
        "da solicitação e elaboração da proposta."
    )

    enviar = st.button(
        "Enviar solicitação",
        type="primary",
        use_container_width=True,
    )

    if not enviar:
        return

    erros = []

    if not _texto(
        nome_responsavel
    ):
        erros.append(
            "Nome do responsável"
        )

    if not _texto(email):
        erros.append(
            "E-mail"
        )

    if not _texto(telefone):
        erros.append(
            "Telefone / WhatsApp"
        )

    faltantes = (
        _validar_obrigatorios(
            perguntas,
            respostas,
            arquivos,
        )
    )

    erros.extend(
        faltantes
    )

    if not aceite:
        erros.append(
            "Confirmação das informações"
        )

    if erros:
        st.error(
            "Preencha os campos obrigatórios "
            "antes de enviar."
        )

        with st.expander(
            "Ver campos pendentes"
        ):
            for item in erros:
                st.write(
                    f"• {item}"
                )

        return

    respostas_formatadas = {}

    for pergunta in perguntas:
        pergunta_id = pergunta["id"]

        tipo_campo = _texto(
            pergunta.get(
                "tipo_campo"
            )
        )

        if tipo_campo in (
            TIPOS_CAMPO_ARQUIVO
        ):
            arquivo = arquivos.get(
                pergunta_id
            )

            respostas_formatadas[
                str(pergunta_id)
            ] = {
                "pergunta": _texto(
                    pergunta.get(
                        "pergunta"
                    )
                ),
                "grupo": _texto(
                    pergunta.get(
                        "grupo"
                    )
                ),
                "tipo_campo": (
                    tipo_campo
                ),
                "resposta": (
                    arquivo.name
                    if arquivo
                    else None
                ),
            }

        else:
            respostas_formatadas[
                str(pergunta_id)
            ] = {
                "pergunta": _texto(
                    pergunta.get(
                        "pergunta"
                    )
                ),
                "grupo": _texto(
                    pergunta.get(
                        "grupo"
                    )
                ),
                "tipo_campo": (
                    tipo_campo
                ),
                "resposta": (
                    respostas.get(
                        str(
                            pergunta_id
                        )
                    )
                ),
            }

    try:
        solicitacao = (
            _salvar_solicitacao(
                supabase=(
                    supabase
                ),
                tipo_constituicao_id=(
                    tipo["id"]
                ),
                nome_empresa=(
                    _texto(
                        nome_empresa
                    )
                ),
                nome_responsavel=(
                    _texto(
                        nome_responsavel
                    )
                ),
                email=_texto(
                    email
                ),
                telefone=_texto(
                    telefone
                ),
                cnpj=_texto(
                    cnpj
                ),
                respostas=(
                    respostas_formatadas
                ),
            )
        )

        _salvar_metadados_arquivos(
            supabase=(
                supabase
            ),
            solicitacao_id=(
                solicitacao["id"]
            ),
            perguntas=perguntas,
            arquivos=arquivos,
        )

    except Exception as erro:
        st.error(
            "Não foi possível enviar a "
            "solicitação. "
            f"Detalhes: {erro}"
        )
        return

    st.success(
        "Solicitação enviada com sucesso."
    )

    st.info(
        "A equipe da Escrita Contabilidade "
        "analisará as informações fornecidas "
        "para dar continuidade ao atendimento."
    )

    st.balloons()
