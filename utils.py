import io
import re
import pandas as pd
import streamlit as st

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_numero_br(valor):
    try:
        valor = float(valor or 0)
    except:
        valor = 0.0

    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def converter_numero_br(texto):
    if texto is None:
        return 0.0

    texto = str(texto).strip()

    if texto == "":
        return 0.0

    texto = texto.replace("R$", "").strip()
    texto = texto.replace(".", "")
    texto = texto.replace(",", ".")

    try:
        return float(texto)
    except:
        return 0.0


def limpar_nome_arquivo(texto):
    texto = str(texto or "").strip()
    texto = re.sub(r'[^A-Za-z0-9._ -]+', '', texto)
    texto = texto.replace(" ", "_")
    return texto or "sem_nome"


def get_drive_service():
    creds_info = dict(st.secrets["gcp_service_account"])
    scopes = ["https://www.googleapis.com/auth/drive.file"]

    credentials = Credentials.from_service_account_info(
        creds_info,
        scopes=scopes
    )

    return build("drive", "v3", credentials=credentials)


def upload_arquivo_para_drive(uploaded_file, nome_empresa, lead_id, pasta_drive_id):
    service = get_drive_service()

    nome_empresa_limpo = limpar_nome_arquivo(nome_empresa)
    nome_original = limpar_nome_arquivo(uploaded_file.name)

    nome_salvo = f"{pd.Timestamp.today().date()}__lead_{lead_id}__{nome_empresa_limpo}__balancete__{nome_original}"

    file_metadata = {
        "name": nome_salvo,
        "parents": [pasta_drive_id]
    }

    file_bytes = io.BytesIO(uploaded_file.getvalue())

    media = MediaIoBaseUpload(
        file_bytes,
        mimetype=uploaded_file.type or "application/octet-stream",
        resumable=True
    )

    arquivo = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink",
        supportsAllDrives=True
    ).execute()

    return {
        "nome_original": uploaded_file.name,
        "nome_salvo": nome_salvo,
        "drive_file_id": arquivo.get("id"),
        "drive_link": arquivo.get("webViewLink"),
        "mime_type": uploaded_file.type
    }


def upload_pdf_proposta_para_drive(caminho_pdf, nome_empresa, orcamento_id, pasta_drive_id):
    service = get_drive_service()

    nome_empresa_limpo = limpar_nome_arquivo(nome_empresa)
    nome_salvo = f"{pd.Timestamp.today().date()}__orcamento_{orcamento_id}__{nome_empresa_limpo}__proposta.pdf"

    file_metadata = {
        "name": nome_salvo,
        "parents": [pasta_drive_id]
    }

    with open(caminho_pdf, "rb") as f:
        file_bytes = io.BytesIO(f.read())

    media = MediaIoBaseUpload(
        file_bytes,
        mimetype="application/pdf",
        resumable=True
    )

    arquivo = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink",
        supportsAllDrives=True
    ).execute()

    return {
        "pdf_nome": nome_salvo,
        "pdf_drive_file_id": arquivo.get("id"),
        "pdf_drive_link": arquivo.get("webViewLink")
    }


def criar_pasta_drive(nome_pasta, pasta_pai_id):
    service = get_drive_service()

    nome_pasta_limpo = limpar_nome_arquivo(nome_pasta)

    file_metadata = {
        "name": nome_pasta_limpo,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [pasta_pai_id]
    }

    pasta = service.files().create(
        body=file_metadata,
        fields="id, webViewLink",
        supportsAllDrives=True
    ).execute()

    return {
        "folder_id": pasta.get("id"),
        "folder_link": pasta.get("webViewLink")
    }
        "pdf_drive_link": arquivo.get("webViewLink")
    }
