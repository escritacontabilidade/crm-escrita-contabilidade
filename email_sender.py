import smtplib
import streamlit as st
from email.message import EmailMessage


def enviar_email_proposta(destinatario, assunto, mensagem, caminho_pdf):
    remetente = st.secrets["EMAIL_REMETENTE"]
    senha = st.secrets["EMAIL_SENHA"]

    email = EmailMessage()
    email["Subject"] = assunto
    email["From"] = remetente
    email["To"] = destinatario

    email.set_content(mensagem)

    with open(caminho_pdf, "rb") as f:
        email.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename="Proposta_Comercial_Escrita.pdf"
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(remetente, senha)
        smtp.send_message(email)

    return True
