import streamlit as st
import pandas as pd

from utils import (
    formatar_moeda,
    formatar_numero_br,
    converter_numero_br,
    criar_pasta_drive
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


def tela_radar(supabase):
    st.title("🛰️ Radar Importador")

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
        
            res = supabase.table("radar_processos").insert(dados).execute()
        
            if res.data:
                st.session_state["radar_proposta_atual"] = res.data[0]
                st.success("Processo Radar salvo e pasta criada no Google Drive.")
                st.link_button("Abrir pasta no Drive", pasta_info["folder_link"])
            else:
                st.warning("A pasta foi criada no Drive, mas o processo não foi salvo no Supabase.")
        
        except Exception as e:
            st.error(f"Erro ao salvar processo Radar: {e}")
