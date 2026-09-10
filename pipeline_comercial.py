import html
import io
from datetime import datetime

import pandas as pd
import streamlit as st
from weasyprint import HTML


STATUS_EM_ABERTO = "Em aberto"
STATUS_APRESENTADO = "Preço apresentado"
STATUS_FECHADO = "Contrato fechado"
STATUS_NEGATIVA = "Negativa"
STATUS_SEM_RESPOSTA = "Sem resposta"

STATUS_PIPELINE = [
    STATUS_EM_ABERTO,
    STATUS_APRESENTADO,
    STATUS_FECHADO,
    STATUS_NEGATIVA,
    STATUS_SEM_RESPOSTA,
]

CORES_STATUS = {
    STATUS_EM_ABERTO: {
        "fundo": "#fff3cd",
        "borda": "#e6c75a",
        "titulo": "#664d03",
    },
    STATUS_APRESENTADO: {
        "fundo": "#cfe2ff",
        "borda": "#7aa7e8",
        "titulo": "#084298",
    },
    STATUS_FECHADO: {
        "fundo": "#d1e7dd",
        "borda": "#75b798",
        "titulo": "#0f5132",
    },
    STATUS_NEGATIVA: {
        "fundo": "#f8d7da",
        "borda": "#dc8c94",
        "titulo": "#842029",
    },
    STATUS_SEM_RESPOSTA: {
        "fundo": "#e2e3e5",
        "borda": "#adb5bd",
        "titulo": "#41464b",
    },
}


def _texto(valor):
    if valor is None:
        return ""
    return str(valor).strip()


def _numero(valor):
    try:
        if valor is None:
            return 0.0
        return float(valor)
    except Exception:
        return 0.0


def _formatar_moeda(valor):
    valor = _numero(valor)

    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")

    return f"R$ {texto}"


def _formatar_data(valor):
    if valor is None or valor == "":
        return "-"

    try:
        data = pd.to_datetime(valor, errors="coerce")

        if pd.isna(data):
            return "-"

        return data.strftime("%d/%m/%Y")
    except Exception:
        return "-"


def _normalizar_status(valor):
    status = _texto(valor)

    if status in STATUS_PIPELINE:
        return status

    return STATUS_EM_ABERTO


def _calcular_dias_em_etapa(row):
    hoje = pd.Timestamp.today().normalize()

    status = _normalizar_status(
        row.get("status_comercial")
    )

    if status == STATUS_APRESENTADO:
        origem = row.get("data_apresentacao")

    elif status == STATUS_FECHADO:
        origem = row.get("data_fechamento")

    elif status == STATUS_NEGATIVA:
        origem = row.get("data_negativa")

    elif status == STATUS_SEM_RESPOSTA:
        origem = (
            row.get("data_apresentacao")
            or row.get("data_criacao")
        )

    else:
        origem = row.get("data_criacao")

    if origem is None or origem == "":
        return None

    try:
        data = pd.to_datetime(
            origem,
            errors="coerce",
        )

        if pd.isna(data):
            return None

        data = data.normalize()

        dias = (hoje - data).days

        if dias < 0:
            return 0

        return int(dias)

    except Exception:
        return None


def _buscar_dados(supabase):
    resposta = (
        supabase
        .table("historico_vendas")
        .select("*")
        .eq("ativo", True)
        .order("data_criacao", desc=True)
        .execute()
    )

    dados = resposta.data or []

    if not dados:
        return pd.DataFrame()

    df = pd.DataFrame(dados)

    if "status_comercial" not in df.columns:
        df["status_comercial"] = STATUS_EM_ABERTO

    df["status_comercial"] = (
        df["status_comercial"]
        .fillna(STATUS_EM_ABERTO)
        .apply(_normalizar_status)
    )

    if "cliente" not in df.columns:
        df["cliente"] = ""

    if "segmento" not in df.columns:
        df["segmento"] = "Não informado"

    if "regime" not in df.columns:
        df["regime"] = ""

    if "responsavel" not in df.columns:
        df["responsavel"] = ""

    if "valor_total" not in df.columns:
        df["valor_total"] = 0.0

    df["cliente"] = (
        df["cliente"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df["segmento"] = (
        df["segmento"]
        .fillna("Não informado")
        .astype(str)
        .str.strip()
        .replace("", "Não informado")
    )

    df["responsavel"] = (
        df["responsavel"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df["valor_total"] = pd.to_numeric(
        df["valor_total"],
        errors="coerce",
    ).fillna(0.0)

    df["dias_etapa"] = df.apply(
        _calcular_dias_em_etapa,
        axis=1,
    )

    return df


def _aplicar_filtros(
    df,
    filtro_status,
    filtro_segmento,
    filtro_responsavel,
    busca_cliente,
):
    dados = df.copy()

    if filtro_status != "Todos":
        dados = dados[
            dados["status_comercial"]
            == filtro_status
        ]

    if filtro_segmento != "Todos":
        dados = dados[
            dados["segmento"]
            == filtro_segmento
        ]

    if filtro_responsavel != "Todos":
        dados = dados[
            dados["responsavel"]
            == filtro_responsavel
        ]

    busca = _texto(busca_cliente).lower()

    if busca:
        dados = dados[
            dados["cliente"]
            .astype(str)
            .str.lower()
            .str.contains(
                busca,
                na=False,
                regex=False,
            )
        ]

    return dados


def _renderizar_card(row):
    status = _normalizar_status(
        row.get("status_comercial")
    )

    cores = CORES_STATUS[status]

    cliente = html.escape(
        _texto(row.get("cliente"))
        or "Cliente não informado"
    )

    segmento = html.escape(
        _texto(row.get("segmento"))
        or "Não informado"
    )

    regime = html.escape(
        _texto(row.get("regime"))
        or "Não informado"
    )

    valor = _formatar_moeda(
        row.get("valor_total")
    )

    dias = row.get("dias_etapa")

    if pd.isna(dias) or dias is None:
        texto_dias = "Tempo na etapa: não informado"
    else:
        texto_dias = (
            f"Tempo na etapa: {int(dias)} dia(s)"
        )

    observacao = html.escape(
        _texto(row.get("observacao_status"))
    )

    bloco_observacao = ""

    if observacao:
        bloco_observacao = f"""
        <div style="
            margin-top:8px;
            font-size:11px;
            color:#5f6670;
            border-top:1px solid rgba(0,0,0,0.08);
            padding-top:6px;
        ">
            {observacao}
        </div>
        """

    st.markdown(
        f"""
        <div style="
            background:{cores['fundo']};
            border:1px solid {cores['borda']};
            border-radius:10px;
            padding:12px;
            margin-bottom:10px;
            box-shadow:0 1px 3px rgba(0,0,0,0.08);
        ">
            <div style="
                font-weight:700;
                font-size:14px;
                color:#111827;
                margin-bottom:8px;
            ">
                {cliente}
            </div>

            <div style="
                font-size:12px;
                color:#4b5563;
                margin-bottom:3px;
            ">
                {segmento}
            </div>

            <div style="
                font-size:12px;
                color:#4b5563;
                margin-bottom:8px;
            ">
                {regime}
            </div>

            <div style="
                font-weight:700;
                font-size:15px;
                color:{cores['titulo']};
                margin-bottom:7px;
            ">
                {valor}
            </div>

            <div style="
                font-size:11px;
                color:#6b7280;
            ">
                {texto_dias}
            </div>

            {bloco_observacao}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _renderizar_kanban(df):
    st.subheader("Pipeline por etapa")

    if df.empty:
        st.info(
            "Nenhuma oportunidade encontrada "
            "para os filtros selecionados."
        )
        return

    colunas = st.columns(
        len(STATUS_PIPELINE)
    )

    for indice, status in enumerate(
        STATUS_PIPELINE
    ):
        dados_status = df[
            df["status_comercial"] == status
        ].copy()

        cores = CORES_STATUS[status]

        with colunas[indice]:
            quantidade = len(dados_status)

            valor_status = (
                dados_status["valor_total"].sum()
                if not dados_status.empty
                else 0
            )

            st.markdown(
                f"""
                <div style="
                    background:{cores['fundo']};
                    border:1px solid {cores['borda']};
                    border-radius:10px;
                    padding:10px;
                    margin-bottom:12px;
                    text-align:center;
                ">
                    <div style="
                        font-size:14px;
                        font-weight:700;
                        color:{cores['titulo']};
                    ">
                        {html.escape(status)}
                    </div>

                    <div style="
                        font-size:20px;
                        font-weight:800;
                        color:#111827;
                        margin-top:4px;
                    ">
                        {quantidade}
                    </div>

                    <div style="
                        font-size:11px;
                        color:#5f6670;
                        margin-top:2px;
                    ">
                        {_formatar_moeda(valor_status)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if dados_status.empty:
                st.caption(
                    "Nenhuma oportunidade."
                )
            else:
                for _, row in (
                    dados_status
                    .sort_values(
                        "valor_total",
                        ascending=False,
                    )
                    .iterrows()
                ):
                    _renderizar_card(row)


def _atualizar_status(
    supabase,
    row,
    novo_status,
    observacao,
):
    historico_id = int(row["id"])

    hoje = (
        pd.Timestamp.today()
        .date()
        .isoformat()
    )

    dados_update = {
        "status_comercial": novo_status,
        "observacao_status": observacao,
    }

    if novo_status == STATUS_APRESENTADO:
        dados_update[
            "data_apresentacao"
        ] = hoje

    elif novo_status == STATUS_FECHADO:
        dados_update[
            "data_fechamento"
        ] = hoje

    elif novo_status == STATUS_NEGATIVA:
        dados_update[
            "data_negativa"
        ] = hoje

    (
        supabase
        .table("historico_vendas")
        .update(dados_update)
        .eq("id", historico_id)
        .execute()
    )

    # =========================================================
    # SINCRONIZA COM O ORÇAMENTO CORRESPONDENTE
    # =========================================================

    orcamento_id = row.get(
        "orcamento_id"
    )

    if (
        orcamento_id is not None
        and not pd.isna(orcamento_id)
    ):
        mapa_orcamento = {
            STATUS_EM_ABERTO: "Em aberto",
            STATUS_APRESENTADO: "Proposta enviada",
            STATUS_FECHADO: "Fechado",
            STATUS_NEGATIVA: "Perdido",
        }

        status_orcamento = (
            mapa_orcamento.get(
                novo_status
            )
        )

        if status_orcamento:
            (
                supabase
                .table("orcamentos")
                .update({
                    "status": status_orcamento,
                    "updated_at": (
                        pd.Timestamp.now()
                        .isoformat()
                    ),
                })
                .eq(
                    "id",
                    int(orcamento_id),
                )
                .execute()
            )

    # =========================================================
    # SINCRONIZA COM LEAD, SE HOUVER VÍNCULO
    # =========================================================

    lead_id = row.get("lead_id")

    if (
        lead_id is not None
        and not pd.isna(lead_id)
    ):
        mapa_lead = {
            STATUS_EM_ABERTO: "Em análise",
            STATUS_APRESENTADO: "Preço apresentado",
            STATUS_FECHADO: "Fechado",
            STATUS_NEGATIVA: "Negativa",
            STATUS_SEM_RESPOSTA: "Sem resposta",
        }

        status_lead = mapa_lead.get(
            novo_status
        )

        if status_lead:
            (
                supabase
                .table("leads_externos")
                .update({
                    "status": status_lead
                })
                .eq(
                    "id",
                    int(lead_id),
                )
                .execute()
            )


def _preparar_excel(df):
    arquivo = io.BytesIO()

    dados = df.copy()

    colunas = [
        "orcamento_id",
        "cliente",
        "segmento",
        "regime",
        "valor_total",
        "status_comercial",
        "data_apresentacao",
        "data_fechamento",
        "data_negativa",
        "dias_etapa",
        "observacao_status",
        "responsavel",
    ]

    colunas = [
        coluna
        for coluna in colunas
        if coluna in dados.columns
    ]

    dados = dados[colunas].copy()

    nomes = {
        "orcamento_id": "Orçamento ID",
        "cliente": "Cliente",
        "segmento": "Segmento",
        "regime": "Regime",
        "valor_total": "Valor",
        "status_comercial": "Status",
        "data_apresentacao": "Data apresentação",
        "data_fechamento": "Data fechamento",
        "data_negativa": "Data negativa",
        "dias_etapa": "Dias na etapa",
        "observacao_status": "Observação",
        "responsavel": "Responsável",
    }

    dados = dados.rename(
        columns=nomes
    )

    resumo = (
        df.groupby(
            "status_comercial",
            dropna=False,
        )
        .agg(
            Quantidade=("id", "count"),
            Valor=("valor_total", "sum"),
        )
        .reset_index()
        .rename(
            columns={
                "status_comercial": "Status"
            }
        )
    )

    with pd.ExcelWriter(
        arquivo,
        engine="openpyxl",
    ) as writer:
        dados.to_excel(
            writer,
            sheet_name="Pipeline",
            index=False,
        )

        resumo.to_excel(
            writer,
            sheet_name="Resumo",
            index=False,
        )

        worksheet = writer.sheets[
            "Pipeline"
        ]

        for coluna in worksheet.columns:
            maior = 0
            letra = coluna[0].column_letter

            for celula in coluna:
                valor = (
                    ""
                    if celula.value is None
                    else str(celula.value)
                )

                maior = max(
                    maior,
                    len(valor),
                )

            worksheet.column_dimensions[
                letra
            ].width = min(
                maior + 2,
                45,
            )

        worksheet.freeze_panes = "A2"

        resumo_ws = writer.sheets[
            "Resumo"
        ]

        for coluna in resumo_ws.columns:
            maior = 0
            letra = coluna[0].column_letter

            for celula in coluna:
                valor = (
                    ""
                    if celula.value is None
                    else str(celula.value)
                )

                maior = max(
                    maior,
                    len(valor),
                )

            resumo_ws.column_dimensions[
                letra
            ].width = min(
                maior + 2,
                35,
            )

    arquivo.seek(0)

    return arquivo.getvalue()


def _preparar_pdf(df):
    total = len(df)

    valor_total = (
        df["valor_total"].sum()
        if not df.empty
        else 0
    )

    blocos_status = ""

    for status in STATUS_PIPELINE:
        dados_status = df[
            df["status_comercial"] == status
        ]

        if dados_status.empty:
            continue

        cores = CORES_STATUS[status]

        linhas = ""

        for _, row in (
            dados_status
            .sort_values(
                "cliente",
                ascending=True,
            )
            .iterrows()
        ):
            linhas += f"""
            <tr>
                <td>
                    {html.escape(_texto(row.get("cliente")))}
                </td>
                <td>
                    {html.escape(_texto(row.get("segmento")))}
                </td>
                <td>
                    {html.escape(_texto(row.get("regime")))}
                </td>
                <td class="valor">
                    {_formatar_moeda(row.get("valor_total"))}
                </td>
                <td>
                    {_formatar_data(row.get("data_apresentacao"))}
                </td>
                <td>
                    {
                        "-"
                        if pd.isna(row.get("dias_etapa"))
                        else str(int(row.get("dias_etapa")))
                    }
                </td>
            </tr>
            """

        total_status = len(
            dados_status
        )

        valor_status = (
            dados_status[
                "valor_total"
            ].sum()
        )

        blocos_status += f"""
        <div class="status-box">
            <div
                class="status-title"
                style="
                    background:{cores['fundo']};
                    border-color:{cores['borda']};
                    color:{cores['titulo']};
                "
            >
                {html.escape(status)}
                — {total_status} oportunidade(s)
                — {_formatar_moeda(valor_status)}
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Cliente</th>
                        <th>Segmento</th>
                        <th>Regime</th>
                        <th>Valor</th>
                        <th>Apresentação</th>
                        <th>Dias</th>
                    </tr>
                </thead>

                <tbody>
                    {linhas}
                </tbody>
            </table>
        </div>
        """

    data_emissao = datetime.now().strftime(
        "%d/%m/%Y %H:%M"
    )

    conteudo = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">

        <style>
            @page {{
                size: A4 landscape;
                margin: 15mm;
            }}

            body {{
                font-family: Arial, sans-serif;
                color: #172033;
                font-size: 10px;
            }}

            h1 {{
                color: #0D2F4F;
                font-size: 22px;
                margin-bottom: 4px;
            }}

            .subtitulo {{
                color: #6b7280;
                margin-bottom: 18px;
            }}

            .resumo {{
                display: flex;
                gap: 12px;
                margin-bottom: 20px;
            }}

            .resumo-card {{
                border: 1px solid #d8dee7;
                border-radius: 8px;
                padding: 10px 14px;
                min-width: 150px;
            }}

            .resumo-label {{
                color: #6b7280;
                font-size: 9px;
            }}

            .resumo-valor {{
                color: #0D2F4F;
                font-size: 16px;
                font-weight: bold;
                margin-top: 4px;
            }}

            .status-box {{
                margin-bottom: 20px;
                page-break-inside: avoid;
            }}

            .status-title {{
                border: 1px solid;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
                font-size: 12px;
                margin-bottom: 6px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
            }}

            th {{
                background: #f3f5f8;
                color: #334155;
                text-align: left;
                padding: 6px;
                border: 1px solid #dde2e8;
            }}

            td {{
                padding: 6px;
                border: 1px solid #e5e7eb;
            }}

            .valor {{
                text-align: right;
                white-space: nowrap;
            }}

            .rodape {{
                margin-top: 15px;
                color: #8b95a5;
                font-size: 8px;
            }}
        </style>
    </head>

    <body>
        <h1>Escrita Contabilidade</h1>

        <div class="subtitulo">
            Relatório do Pipeline Comercial
            — Emitido em {data_emissao}
        </div>

        <div class="resumo">
            <div class="resumo-card">
                <div class="resumo-label">
                    Oportunidades
                </div>

                <div class="resumo-valor">
                    {total}
                </div>
            </div>

            <div class="resumo-card">
                <div class="resumo-label">
                    Valor total
                </div>

                <div class="resumo-valor">
                    {_formatar_moeda(valor_total)}
                </div>
            </div>
        </div>

        {blocos_status}

        <div class="rodape">
            Relatório gerado pelo CRM &
            Precificação Escrita Contabilidade.
        </div>
    </body>
    </html>
    """

    return HTML(
        string=conteudo
    ).write_pdf()


def _renderizar_indicadores(df):
    total = len(df)

    valor_total = (
        df["valor_total"].sum()
        if not df.empty
        else 0
    )

    apresentados = len(
        df[
            df["status_comercial"]
            == STATUS_APRESENTADO
        ]
    )

    fechados = len(
        df[
            df["status_comercial"]
            == STATUS_FECHADO
        ]
    )

    negativas = len(
        df[
            df["status_comercial"]
            == STATUS_NEGATIVA
        ]
    )

    col1, col2, col3, col4, col5 = (
        st.columns(5)
    )

    col1.metric(
        "Oportunidades",
        total,
    )

    col2.metric(
        "Valor em pipeline",
        _formatar_moeda(valor_total),
    )

    col3.metric(
        "Preço apresentado",
        apresentados,
    )

    col4.metric(
        "Contratos fechados",
        fechados,
    )

    col5.metric(
        "Negativas",
        negativas,
    )


def _renderizar_editor_status(
    supabase,
    df,
):
    st.subheader(
        "Atualizar oportunidade"
    )

    opcoes = []

    mapa_linhas = {}

    for _, row in df.iterrows():
        identificador = (
            f"{int(row['id'])} | "
            f"{_texto(row.get('cliente'))} | "
            f"{_formatar_moeda(row.get('valor_total'))}"
        )

        opcoes.append(
            identificador
        )

        mapa_linhas[
            identificador
        ] = row

    if not opcoes:
        st.info(
            "Nenhuma oportunidade disponível "
            "para atualização."
        )
        return

    selecionado = st.selectbox(
        "Selecione uma oportunidade",
        opcoes,
        key="pipeline_oportunidade",
    )

    row = mapa_linhas[
        selecionado
    ]

    status_atual = _normalizar_status(
        row.get("status_comercial")
    )

    indice_status = (
        STATUS_PIPELINE.index(
            status_atual
        )
    )

    novo_status = st.selectbox(
        "Novo status",
        STATUS_PIPELINE,
        index=indice_status,
        key="pipeline_novo_status",
    )

    observacao_atual = _texto(
        row.get("observacao_status")
    )

    observacao = st.text_input(
        "Observação do status",
        value=observacao_atual,
        key="pipeline_observacao",
    )

    if st.button(
        "Salvar status comercial",
        key="pipeline_salvar_status",
    ):
        try:
            _atualizar_status(
                supabase=supabase,
                row=row,
                novo_status=novo_status,
                observacao=observacao,
            )

            st.success(
                "Status atualizado com sucesso."
            )

            st.rerun()

        except Exception as erro:
            st.error(
                "Erro ao atualizar status: "
                f"{erro}"
            )


def tela_pipeline_comercial(
    supabase,
):
    st.title("📌 Pipeline Comercial")

    st.caption(
        "Acompanhe as oportunidades comerciais "
        "por etapa, atualize os status e exporte "
        "os dados para Excel ou PDF."
    )

    try:
        df = _buscar_dados(
            supabase
        )

    except Exception as erro:
        st.error(
            "Não foi possível carregar "
            "o Pipeline Comercial: "
            f"{erro}"
        )
        return

    if df.empty:
        st.info(
            "Nenhuma oportunidade comercial "
            "ativa encontrada."
        )
        return

    # =========================================================
    # INDICADORES
    # =========================================================

    _renderizar_indicadores(
        df
    )

    st.divider()

    # =========================================================
    # FILTROS
    # =========================================================

    st.subheader("Filtros")

    segmentos = sorted(
        [
            item
            for item in df[
                "segmento"
            ].dropna().unique()
            if _texto(item)
        ]
    )

    responsaveis = sorted(
        [
            item
            for item in df[
                "responsavel"
            ].dropna().unique()
            if _texto(item)
        ]
    )

    f1, f2, f3, f4 = st.columns(
        [1, 1.3, 1.3, 1.7]
    )

    with f1:
        filtro_status = st.selectbox(
            "Status",
            ["Todos"] + STATUS_PIPELINE,
            key="pipeline_filtro_status",
        )

    with f2:
        filtro_segmento = st.selectbox(
            "Segmento",
            ["Todos"] + segmentos,
            key="pipeline_filtro_segmento",
        )

    with f3:
        filtro_responsavel = st.selectbox(
            "Responsável",
            ["Todos"] + responsaveis,
            key="pipeline_filtro_responsavel",
        )

    with f4:
        busca_cliente = st.text_input(
            "Buscar cliente",
            placeholder="Digite parte do nome...",
            key="pipeline_busca_cliente",
        )

    df_filtrado = _aplicar_filtros(
        df=df,
        filtro_status=filtro_status,
        filtro_segmento=filtro_segmento,
        filtro_responsavel=filtro_responsavel,
        busca_cliente=busca_cliente,
    )

    st.caption(
        f"{len(df_filtrado)} oportunidade(s) "
        "nos filtros atuais."
    )

    # =========================================================
    # EXPORTAÇÃO
    # =========================================================

    st.subheader("Exportar")

    ex1, ex2 = st.columns(2)

    with ex1:
        try:
            arquivo_excel = _preparar_excel(
                df_filtrado
            )

            st.download_button(
                "📊 Baixar Excel",
                data=arquivo_excel,
                file_name=(
                    "Pipeline_Comercial_"
                    f"{datetime.now().strftime('%Y%m%d')}.xlsx"
                ),
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                use_container_width=True,
            )

        except Exception as erro:
            st.warning(
                "Não foi possível preparar "
                f"o Excel: {erro}"
            )

    with ex2:
        if st.button(
            "📄 Preparar PDF",
            use_container_width=True,
            key="pipeline_preparar_pdf",
        ):
            try:
                st.session_state[
                    "pipeline_pdf"
                ] = _preparar_pdf(
                    df_filtrado
                )

                st.success(
                    "PDF preparado."
                )

            except Exception as erro:
                st.error(
                    "Não foi possível gerar "
                    f"o PDF: {erro}"
                )

        pdf_gerado = st.session_state.get(
            "pipeline_pdf"
        )

        if pdf_gerado:
            st.download_button(
                "⬇️ Baixar PDF",
                data=pdf_gerado,
                file_name=(
                    "Pipeline_Comercial_"
                    f"{datetime.now().strftime('%Y%m%d')}.pdf"
                ),
                mime="application/pdf",
                use_container_width=True,
            )

    st.divider()

    # =========================================================
    # KANBAN
    # =========================================================

    _renderizar_kanban(
        df_filtrado
    )

    st.divider()

    # =========================================================
    # ATUALIZAÇÃO DE STATUS
    # =========================================================

    _renderizar_editor_status(
        supabase=supabase,
        df=df_filtrado,
    )
