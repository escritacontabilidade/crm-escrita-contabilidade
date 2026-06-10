import streamlit as st
import pandas as pd

from utils import (
    formatar_moeda,
    formatar_numero_br,
    converter_numero_br,
    criar_pasta_drive,
    upload_documento_radar_para_drive
)


DOCUMENTOS_RADAR = [
    ("Documento de identificação do responsável", "Obrigatório"),
    ("Contrato Social", "Obrigatório"),
    ("Certidão Junta Comercial", "Obrigatório"),
    ("Conta de energia dos últimos 3 meses", 'Dispensado se a empresa estiver estabelecida em "coworking"'),
    ("Plano de internet dos últimos 3 meses", 'Dispensado se a empresa estiver estabelecida em "coworking"'),
    ("Guia de IPTU", 'Dispensado se a empresa estiver estabelecida em "coworking"'),
    ("Escritura do imóvel", "Imóvel próprio"),
    ("Contrato de locação e pagamentos dos últimos 3 meses", "Imóvel alugado e coworking, não esquecer do adendo da PF para empresa"),
    ("Comprovante Espaço Armazenamento", "Obrigatório se não houver espaço físico na empresa para armazenamento das mercadorias"),
    ("Extratos Bancários dos últimos 3 meses", "Obrigatório"),
    ("Balancete de Verificação dos últimos 3 meses", "Obrigatório"),
    ("Comprovante de transferência de recursos", "Obrigatório quando houver obtenção de empréstimo ou mútuo"),
    ("Contrato de Empréstimo Bancário", "Situação especial: se houver recursos oriundos de empréstimos"),
    ("Contrato de Mútuo Registrado em Cartório", "Situação especial: se houver recursos oriundos de mútuos"),
    ("Identificação do remetente dos recursos (mútuo)", "Situação especial: se houver recursos oriundos de mútuos"),
    ("Mutuante PJ - Escrituração Contábil 3 meses", "Situação especial: se houver recursos oriundos de mútuos"),
    ("Comprovante Recolhimento IOF Contrato Mútuo PJ", "Situação especial: se houver recursos oriundos de mútuos"),
    ("Extratos Bancários no mês do aporte", "Situação especial: empresa constituída com aumento de capital nos últimos 5 anos"),
    ("Balanço Patrimonial", "Situação especial: empresa constituída com aumento de capital nos últimos 5 anos"),
    ("Comprovante de transferência de recursos (capital social)", "Situação especial: empresa constituída com aumento de capital nos últimos 5 anos"),
]


def calcular_percentual_checklist(checklist):
    if not checklist:
        return 0

    total = len(checklist)
    concluidos = 0

    for item in checklist:
        status = str(item.get("status", "")).strip()
        if status in ["Enviado", "Dispensado", "Não aplicável"]:
            concluidos += 1

    return round((concluidos / total) * 100, 1)


def tela_novo_processo_radar(supabase):
    st.info("Módulo para proposta e checklist documental do pedido de revisão de Radar.")

    st.subheader("Dados da proposta")

    col1, col2 = st.columns(2)

    with col1:
        nome_empresa = st.text_input("Nome da empresa")
        modalidade = st.selectbox(
            "Modalidade",
            [
                "Limitada US$ 150 mil por semestre",
                "Ilimitada"
            ]
        )

    with col2:
        tipo_cliente = st.selectbox(
            "Tipo de cliente",
            ["Não cliente", "Cliente"]
        )

        valor_padrao = 5000.0 if tipo_cliente == "Cliente" else 6300.0

        honorario_txt = st.text_input(
            "Honorários",
            value=formatar_numero_br(valor_padrao)
        )

        honorario = converter_numero_br(honorario_txt)

    st.divider()

    if modalidade == "Limitada US$ 150 mil por semestre":
        disponibilidade_usd = 50000
        disponibilidade_brl = 265380
    else:
        disponibilidade_usd = 150000
        disponibilidade_brl = 796140

    st.subheader("Capacidade financeira exigida")

    c1, c2 = st.columns(2)
    c1.metric("Disponibilidade em dólar", f"US$ {disponibilidade_usd:,.2f}")
    c2.metric("Equivalente em reais", formatar_moeda(disponibilidade_brl))

    st.caption("Câmbio utilizado: R$ 5,3076 conforme referência informada pelo cliente.")

    st.divider()

    st.subheader("Checklist documental")

    checklist = []

    for i, (documento, observacao) in enumerate(DOCUMENTOS_RADAR, start=1):
        with st.expander(f"{i}. {documento}"):
            st.write(f"**Observação:** {observacao}")

            status = st.selectbox(
                "Status",
                ["Pendente", "Enviado", "Dispensado", "Não aplicável"],
                key=f"radar_status_{i}"
            )

            arquivo = st.file_uploader(
                "Anexar documento",
                type=["pdf", "png", "jpg", "jpeg", "xlsx", "xlsm", "doc", "docx"],
                key=f"radar_doc_{i}"
            )

            comentario = st.text_area(
                "Observação interna",
                key=f"radar_obs_{i}"
            )

            checklist.append({
                "documento": documento,
                "observacao": observacao,
                "status": status,
                "arquivo_obj": arquivo,
                "arquivo": arquivo.name if arquivo else None,
                "comentario": comentario
            })

    st.divider()

    if st.button("Salvar proposta Radar"):
        if not nome_empresa:
            st.warning("Informe o nome da empresa.")
            st.stop()

        dados = {
            "nome_empresa": nome_empresa,
            "modalidade": modalidade,
            "tipo_cliente": tipo_cliente,
            "honorario": honorario,
            "disponibilidade_usd": disponibilidade_usd,
            "disponibilidade_brl": disponibilidade_brl,
            "checklist": checklist,
            "status": "Em aberto",
            "created_at": pd.Timestamp.now().isoformat()
        }

        try:
            pasta_pai_id = st.secrets["drive_radar_folder_id"]

            pasta_info = criar_pasta_drive(
                nome_pasta=f"RADAR__{nome_empresa}",
                pasta_pai_id=pasta_pai_id
            )

            dados["drive_folder_id"] = pasta_info["folder_id"]
            dados["drive_folder_link"] = pasta_info["folder_link"]

            for item in checklist:
                arquivo_obj = item.get("arquivo_obj")

                if arquivo_obj:
                    upload_info = upload_documento_radar_para_drive(
                        uploaded_file=arquivo_obj,
                        nome_empresa=nome_empresa,
                        documento_nome=item["documento"],
                        pasta_drive_id=pasta_info["folder_id"]
                    )

                    item["drive_link"] = upload_info["drive_link"]
                    item["drive_file_id"] = upload_info["drive_file_id"]

                item.pop("arquivo_obj", None)

            res = supabase.table("radar_processos").insert(dados).execute()

            if res.data:
                st.session_state["radar_proposta_atual"] = res.data[0]
                st.success("Processo Radar salvo e pasta criada no Google Drive.")
                st.link_button("Abrir pasta no Drive", pasta_info["folder_link"])
            else:
                st.warning("A pasta foi criada no Drive, mas o processo não foi salvo no Supabase.")

        except Exception as e:
            st.error(f"Erro ao salvar processo Radar: {e}")


def tela_processos_radar(supabase):
    st.subheader("Processos Radar")

    try:
        res = supabase.table("radar_processos") \
            .select("*") \
            .eq("ativo", True) \
            .order("created_at", desc=True) \
            .execute()

        if not res.data:
            st.info("Nenhum processo Radar salvo ainda.")
            return

        df = pd.DataFrame(res.data)

        df["percentual_checklist"] = df["checklist"].apply(calcular_percentual_checklist)

        colunas = [
            "id",
            "nome_empresa",
            "modalidade",
            "tipo_cliente",
            "honorario",
            "status",
            "percentual_checklist",
            "created_at",
            "drive_folder_link"
        ]

        colunas = [c for c in colunas if c in df.columns]

        st.dataframe(df[colunas], use_container_width=True)

        opcoes = [
            f"{row['id']} | {row.get('nome_empresa', '')} | {row.get('status', '')} | {row.get('percentual_checklist', 0)}%"
            for _, row in df.iterrows()
        ]

        escolhido = st.selectbox("Selecione um processo Radar", opcoes)

        processo_id = int(escolhido.split("|")[0].strip())
        processo = df[df["id"] == processo_id].iloc[0].to_dict()

        st.divider()
        st.subheader("Detalhes do processo")

        c1, c2, c3 = st.columns(3)
        c1.metric("Empresa", processo.get("nome_empresa", ""))
        c2.metric("Modalidade", processo.get("modalidade", ""))
        c3.metric("Checklist", f"{processo.get('percentual_checklist', 0)}%")

        novo_status = st.selectbox(
            "Status do processo",
            ["Em aberto", "Em análise", "Aguardando documentos", "Documentos completos", "Protocolado", "Concluído", "Arquivado"],
            index=["Em aberto", "Em análise", "Aguardando documentos", "Documentos completos", "Protocolado", "Concluído", "Arquivado"].index(
                processo.get("status") if processo.get("status") in ["Em aberto", "Em análise", "Aguardando documentos", "Documentos completos", "Protocolado", "Concluído", "Arquivado"] else "Em aberto"
            )
        )

        novo_honorario_txt = st.text_input(
            "Honorários",
            value=formatar_numero_br(processo.get("honorario") or 0)
        )

        novo_honorario = converter_numero_br(novo_honorario_txt)

        checklist = processo.get("checklist") or []

        st.subheader("Checklist salvo")

        for i, item in enumerate(checklist, start=1):
            status_item = str(item.get("status", "")).strip()
        
            if status_item == "Enviado":
                icone = "🟢"
            elif status_item in ["Dispensado", "Não aplicável"]:
                icone = "🔵"
            else:
                icone = "🔴"
        
            titulo = f"{icone} {i}. {item.get('documento', '')} — {status_item}"
        
            with st.expander(titulo):
                st.write(f"**Observação:** {item.get('observacao', '')}")
                st.write(f"**Status:** {item.get('status', '')}")
                st.write(f"**Comentário:** {item.get('comentario', '')}")

                if item.get("drive_link"):
                    st.link_button("Abrir documento", item.get("drive_link"))

        if processo.get("drive_folder_link"):
            st.link_button("Abrir pasta do processo no Drive", processo.get("drive_folder_link"))

        if st.button("Salvar alterações do processo Radar"):
            supabase.table("radar_processos").update({
                "status": novo_status,
                "honorario": novo_honorario,
                "updated_at": pd.Timestamp.now().isoformat()
            }).eq("id", processo_id).execute()

            st.success("Processo Radar atualizado com sucesso.")
            st.rerun()

    except Exception as e:
        st.error(f"Erro ao carregar processos Radar: {e}")


def tela_radar(supabase):
    st.title("🛰️ Radar Importador")

    aba_novo, aba_processos = st.tabs(["Novo Processo", "Processos Radar"])

    with aba_novo:
        tela_novo_processo_radar(supabase)

    with aba_processos:
        tela_processos_radar(supabase)

def tela_cliente_radar(supabase, token):
    st.image("Logo Escrita.png", width=200)
    st.title("📎 Envio de Documentos - Radar Importador")

    try:
        res = supabase.table("radar_processos") \
            .select("*") \
            .eq("token_cliente", token) \
            .eq("ativo", True) \
            .limit(1) \
            .execute()

        if not res.data:
            st.error("Link inválido ou processo não encontrado.")
            st.stop()

        processo = res.data[0]
        processo_id = processo["id"]

        st.subheader("Dados cadastrais")

        with st.form("form_cliente_radar"):
            razao_social = st.text_input("Razão Social", value=processo.get("razao_social") or processo.get("nome_empresa") or "")
            cnpj = st.text_input("CNPJ", value=processo.get("cnpj") or "")
            responsavel = st.text_input("Responsável", value=processo.get("responsavel") or "")
            email = st.text_input("E-mail", value=processo.get("email") or "")
            telefone = st.text_input("Telefone / WhatsApp", value=processo.get("telefone") or "")

            salvar_dados = st.form_submit_button("Salvar dados cadastrais")

            if salvar_dados:
                supabase.table("radar_processos").update({
                    "razao_social": razao_social,
                    "cnpj": cnpj,
                    "responsavel": responsavel,
                    "email": email,
                    "telefone": telefone,
                    "dados_cliente_preenchidos": True,
                    "updated_at": pd.Timestamp.now().isoformat()
                }).eq("id", processo_id).execute()

                st.success("Dados cadastrais salvos com sucesso.")
                st.rerun()

        st.divider()
        st.subheader("Checklist de documentos")

        checklist = processo.get("checklist") or []

        for i, item in enumerate(checklist, start=1):
            status_atual = item.get("status", "Pendente")

            if status_atual == "Enviado":
                icone = "🟢"
            elif status_atual in ["Dispensado", "Não aplicável"]:
                icone = "🔵"
            else:
                icone = "🔴"

            with st.expander(f"{icone} {i}. {item.get('documento', '')} — {status_atual}"):
                st.write(f"**Observação:** {item.get('observacao', '')}")

                if item.get("drive_link"):
                    st.success("Documento já enviado.")
                    st.link_button("Abrir documento enviado", item.get("drive_link"))
                else:
                    arquivo = st.file_uploader(
                        "Anexar documento",
                        type=["pdf", "png", "jpg", "jpeg", "xlsx", "xlsm", "doc", "docx"],
                        key=f"cliente_radar_upload_{processo_id}_{i}"
                    )

                    if st.button("Enviar este documento", key=f"cliente_radar_btn_{processo_id}_{i}"):
                        if not arquivo:
                            st.warning("Selecione um arquivo antes de enviar.")
                            st.stop()

                        pasta_drive_id = processo.get("drive_folder_id")

                        if not pasta_drive_id:
                            st.error("Pasta do processo no Drive não encontrada.")
                            st.stop()

                        upload_info = upload_documento_radar_para_drive(
                            uploaded_file=arquivo,
                            nome_empresa=razao_social or processo.get("nome_empresa"),
                            documento_nome=item.get("documento"),
                            pasta_drive_id=pasta_drive_id
                        )

                        item["status"] = "Enviado"
                        item["arquivo"] = arquivo.name
                        item["drive_link"] = upload_info["drive_link"]
                        item["drive_file_id"] = upload_info["drive_file_id"]

                        supabase.table("radar_processos").update({
                            "checklist": checklist,
                            "updated_at": pd.Timestamp.now().isoformat()
                        }).eq("id", processo_id).execute()

                        st.success("Documento enviado com sucesso.")
                        st.rerun()

    except Exception as e:
        st.error(f"Erro no portal Radar: {e}")
