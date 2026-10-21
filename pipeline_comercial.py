import html
import io
from datetime import datetime, date
import calendar

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

    if "classificacao_lead" not in df.columns:
        df["classificacao_lead"] = ""
    df["classificacao_lead"] = df["classificacao_lead"].fillna("").astype(str).str.strip()

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

    valor = html.escape(
        _formatar_moeda(
            row.get("valor_total")
        )
    )

    dias = row.get("dias_etapa")

    if pd.isna(dias) or dias is None:
        texto_dias = "Tempo na etapa: não informado"
    else:
        texto_dias = (
            f"Tempo na etapa: {int(dias)} dia(s)"
        )

    texto_dias = html.escape(texto_dias)

    observacao = html.escape(
        _texto(row.get("observacao_status"))
    )

    bloco_observacao = ""

    if observacao:
        bloco_observacao = (
            '<div style="margin-top:8px;font-size:11px;color:#5f6670;'
            'border-top:1px solid rgba(0,0,0,0.08);padding-top:6px;">'
            f'{observacao}'
            '</div>'
        )

    card_html = (
        f'<div style="background:{cores["fundo"]};'
        f'border:1px solid {cores["borda"]};'
        'border-radius:10px;padding:12px;margin-bottom:10px;'
        'box-shadow:0 1px 3px rgba(0,0,0,0.08);">'
        '<div style="font-weight:700;font-size:14px;color:#111827;'
        f'margin-bottom:8px;">{cliente}</div>'
        '<div style="font-size:12px;color:#4b5563;margin-bottom:3px;">'
        f'{segmento}</div>'
        '<div style="font-size:12px;color:#4b5563;margin-bottom:8px;">'
        f'{regime}</div>'
        f'<div style="font-weight:700;font-size:15px;color:{cores["titulo"]};'
        f'margin-bottom:7px;">{valor}</div>'
        '<div style="font-size:11px;color:#6b7280;">'
        f'{texto_dias}</div>'
        f'{bloco_observacao}'
        '</div>'
    )

    st.markdown(
        card_html,
        unsafe_allow_html=True,
    )


def _renderizar_classificacao_lead(supabase, row):
    """Editor persistente por oportunidade fechada; não modifica status."""
    registro_id = int(row["id"])
    atual = _texto(row.get("classificacao_lead"))
    opcoes = ["Não classificado", "Novo", "Antigo", "Personalizado"]
    selecionado_atual = atual if atual in ("Novo", "Antigo") else (
        "Personalizado" if atual else "Não classificado"
    )
    escolha = st.selectbox(
        "Lead Novo?", opcoes, index=opcoes.index(selecionado_atual),
        key=f"pipeline_classificacao_{registro_id}",
    )
    personalizado = ""
    if escolha == "Personalizado":
        personalizado = st.text_input(
            "Indicador", value=atual if selecionado_atual == "Personalizado" else "",
            key=f"pipeline_indicador_{registro_id}",
            placeholder="Ex.: Fenix, HKTC, Mauro",
        )
    novo_valor = (personalizado.strip() if escolha == "Personalizado" else
                  "" if escolha == "Não classificado" else escolha)
    if st.button("Salvar classificação", key=f"pipeline_salvar_classificacao_{registro_id}"):
        if escolha == "Personalizado" and not novo_valor:
            st.warning("Informe o indicador personalizado.")
            return
        try:
            supabase.table("historico_vendas").update(
                {"classificacao_lead": novo_valor or None}
            ).eq("id", registro_id).eq("status_comercial", STATUS_FECHADO).execute()
            st.success("Classificação salva.")
            st.rerun()
        except Exception as erro:
            st.error(f"Não foi possível salvar a classificação: {erro}")


def _renderizar_kanban(df, supabase):
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

            cabecalho_html = (
                f'<div style="background:{cores["fundo"]};'
                f'border:1px solid {cores["borda"]};'
                'border-radius:10px;padding:10px;margin-bottom:12px;'
                'text-align:center;">'
                f'<div style="font-size:14px;font-weight:700;color:{cores["titulo"]};">'
                f'{html.escape(status)}</div>'
                '<div style="font-size:20px;font-weight:800;color:#111827;'
                f'margin-top:4px;">{quantidade}</div>'
                '<div style="font-size:11px;color:#5f6670;margin-top:2px;">'
                f'{html.escape(_formatar_moeda(valor_status))}</div>'
                '</div>'
            )

            st.markdown(
                cabecalho_html,
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
                    if status == STATUS_FECHADO:
                        with st.container(border=True):
                            _renderizar_card(row)
                            _renderizar_classificacao_lead(supabase, row)
                    else:
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
        "classificacao_lead",
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
        "classificacao_lead": "Lead Novo?",
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


MESES_PIPELINE = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def _periodo_pipeline():
    """Períodos idênticos aos do Dashboard, com chaves independentes."""
    st.subheader("Período de análise")
    opcoes = ["Todo o período", "Mês", "Bimestre", "Trimestre",
              "Quadrimestre", "Semestre", "Ano", "Personalizado"]
    c1, c2, c3 = st.columns([1.5, 1, 1.4])
    with c1:
        tipo = st.selectbox("Agrupamento", opcoes, key="pipeline_periodo_tipo")
    if tipo == "Todo o período":
        return None, None, "Todo o período"
    hoje = date.today()
    if tipo == "Personalizado":
        with c2:
            inicio = st.date_input("Data inicial", value=date(hoje.year, 1, 1),
                                   key="pipeline_data_inicio")
        with c3:
            fim = st.date_input("Data final", value=hoje,
                                key="pipeline_data_fim")
        if inicio > fim:
            st.error("A data inicial não pode ser posterior à data final.")
            st.stop()
        return inicio, fim, f"{inicio:%d/%m/%Y} a {fim:%d/%m/%Y}"
    with c2:
        ano = st.number_input("Ano", min_value=2000, max_value=2100,
                              value=hoje.year, step=1, key="pipeline_ano")
    if tipo == "Ano":
        return date(ano, 1, 1), date(ano, 12, 31), str(ano)
    tamanho = {"Mês": 1, "Bimestre": 2, "Trimestre": 3,
               "Quadrimestre": 4, "Semestre": 6}[tipo]
    with c3:
        mes = st.selectbox(
            tipo, list(range(1, 13, tamanho)),
            format_func=lambda m: MESES_PIPELINE[m - 1] if tamanho == 1
            else f"{MESES_PIPELINE[m - 1]} a {MESES_PIPELINE[m + tamanho - 2]}",
            index=(hoje.month - 1) // tamanho,
            key="pipeline_periodo_indice",
        )
    ultimo = mes + tamanho - 1
    return (date(ano, mes, 1),
            date(ano, ultimo, calendar.monthrange(ano, ultimo)[1]),
            f"{MESES_PIPELINE[mes - 1]} a {MESES_PIPELINE[ultimo - 1]} / {ano}")


def _filtrar_data(df, coluna, inicio, fim):
    if inicio is None and fim is None:
        return df.copy()
    if coluna not in df.columns:
        return df.iloc[0:0].copy()
    datas = pd.to_datetime(df[coluna], errors="coerce", utc=True)
    return df.loc[(datas.dt.date >= inicio) & (datas.dt.date <= fim)].copy()


def _filtrar_movimentacoes(df, inicio, fim):
    """Oportunidades com ao menos um evento datado no intervalo.

    A mesma oportunidade aparece apenas uma vez, mesmo quando possui
    apresentação e fechamento no período. Não se inventam datas.
    """
    if inicio is None and fim is None:
        return df.copy()
    if df.empty:
        return df.copy()
    mascara = pd.Series(False, index=df.index)
    for coluna in ("data_apresentacao", "data_fechamento", "data_negativa"):
        if coluna in df.columns:
            datas = pd.to_datetime(df[coluna], errors="coerce", utc=True).dt.date
            mascara = mascara | ((datas >= inicio) & (datas <= fim)).fillna(False)
    return df.loc[mascara].copy()


def _movimentacoes_pipeline(df, inicio, fim):
    """Eventos datados, separados do retrato atual da carteira."""
    if inicio is None:
        return
    apresentados = _filtrar_data(df, "data_apresentacao", inicio, fim)
    fechados = _filtrar_data(df, "data_fechamento", inicio, fim)
    fechados = fechados[fechados["status_comercial"] == STATUS_FECHADO]
    negativas = _filtrar_data(df, "data_negativa", inicio, fim)
    negativas = negativas[negativas["status_comercial"] == STATUS_NEGATIVA]
    st.subheader("Movimentações comerciais no período")
    c1, c2, c3 = st.columns(3)
    c1.metric("Apresentações registradas", len(apresentados))
    c2.metric("Fechamentos no período", len(fechados))
    c3.metric("Negativas no período", len(negativas))
    st.caption("Contagem por datas registradas. Eventos sem data não são "
               "atribuídos artificialmente a nenhum período.")


def _renderizar_indicadores(df):
    """Indicadores da carteira ativa, com etapas atuais e avanço comercial separados."""
    total = len(df)

    if df.empty:
        valor_em_andamento = 0.0
        propostas_apresentadas = 0
        aguardando_decisao = 0
        fechados = 0
        negativas = 0
    else:
        status = df["status_comercial"]
        # Pipeline em andamento: somente etapas Em aberto e Preço apresentado.
        valor_em_andamento = df.loc[
            status.isin([STATUS_EM_ABERTO, STATUS_APRESENTADO]),
            "valor_total",
        ].sum()

        # Avançaram além de Em aberto, mesmo que já tenham sido encerradas.
        propostas_apresentadas = int(status.isin([
            STATUS_APRESENTADO,
            STATUS_FECHADO,
            STATUS_NEGATIVA,
            STATUS_SEM_RESPOSTA,
        ]).sum())

        # Fotografia da etapa atual, distinta do total acumulado apresentado.
        aguardando_decisao = int((status == STATUS_APRESENTADO).sum())
        fechados = int((status == STATUS_FECHADO).sum())
        negativas = int((status == STATUS_NEGATIVA).sum())

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Oportunidades", total)
    col2.metric("Valor em pipeline", _formatar_moeda(valor_em_andamento))
    col3.metric("Propostas apresentadas", propostas_apresentadas)
    col4.metric("Aguardando decisão", aguardando_decisao)
    col5.metric("Contratos fechados", fechados)
    col6.metric("Negativas", negativas)

    st.caption(
        "Valor em pipeline: Em aberto + Preço apresentado. "
        "Propostas apresentadas: oportunidades que avançaram além de Em aberto "
        "(inclui fechadas, negativas e sem resposta). "
        "Aguardando decisão: oportunidades atualmente em Preço apresentado."
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

    inicio, fim, periodo = _periodo_pipeline()
    st.caption(f"Período selecionado: {periodo}.")

    # A carteira é uma fotografia do status atual das oportunidades
    # criadas no período; movimentações usam as datas dos eventos.
    df_periodo = _filtrar_data(df, "data_criacao", inicio, fim)
    st.caption("Carteira por data de criação da oportunidade; status e "
               "valores representam a situação atual, não a situação histórica.")
    _renderizar_indicadores(df_periodo)
    _movimentacoes_pipeline(df, inicio, fim)

    st.divider()

    st.subheader("Visualização das oportunidades")
    modo_visualizacao = st.radio(
        "Critério para o Kanban, a lista de atualização e as exportações",
        ["Carteira por criação", "Movimentações do período"],
        horizontal=True,
        key="pipeline_modo_visualizacao",
    )
    if modo_visualizacao == "Movimentações do período":
        df_visualizacao = _filtrar_movimentacoes(df, inicio, fim)
        st.caption(
            "Exibe oportunidades com apresentação, fechamento ou negativa "
            "registrada no período, mesmo que tenham sido criadas antes. "
            "Cada oportunidade aparece uma única vez, em seu status atual. "
            "Eventos sem data não entram nessa visualização."
        )
    else:
        df_visualizacao = df_periodo
        st.caption(
            "Exibe oportunidades criadas no período selecionado, "
            "com o status comercial atual."
        )

    # =========================================================
    # FILTROS
    # =========================================================

    st.subheader("Filtros")

    segmentos = sorted(
        [
            item
            for item in df_visualizacao[
                "segmento"
            ].dropna().unique()
            if _texto(item)
        ]
    )

    responsaveis = sorted(
        [
            item
            for item in df_visualizacao[
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
        df=df_visualizacao,
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

    st.subheader("Relatório de contratos fechados")
    fechados = df_filtrado[df_filtrado["status_comercial"] == STATUS_FECHADO].copy()
    classes = sorted(c for c in fechados["classificacao_lead"].dropna().unique() if c)
    filtro_classificacao = st.selectbox(
        "Classificação do lead", ["Todas", "Não classificado"] + classes,
        key="pipeline_filtro_classificacao_fechados",
    )
    if filtro_classificacao == "Não classificado":
        fechados = fechados[fechados["classificacao_lead"] == ""]
    elif filtro_classificacao != "Todas":
        fechados = fechados[fechados["classificacao_lead"] == filtro_classificacao]
    st.caption(f"{len(fechados)} contrato(s) fechado(s) | "
               f"Valor: {_formatar_moeda(fechados['valor_total'].sum())}")
    if not fechados.empty:
        st.download_button(
            "Baixar contratos fechados (Excel)",
            data=_preparar_excel(fechados),
            file_name=f"Contratos_Fechados_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="pipeline_excel_fechados",
        )

    st.divider()

    # =========================================================
    # KANBAN
    # =========================================================

    _renderizar_kanban(
        df_filtrado, supabase
    )

    st.divider()

    # =========================================================
    # ATUALIZAÇÃO DE STATUS
    # =========================================================

    _renderizar_editor_status(
        supabase=supabase,
        df=df_filtrado,
    )
