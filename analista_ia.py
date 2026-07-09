import google.generativeai as genai
import streamlit as st

def analisar_empresa(dados_empresa):

    genai.configure(
        api_key=st.secrets["GEMINI_API_KEY"]
    )

    model = genai.GenerativeModel(
        "gemini-2.5-flash"
    )

    prompt = f"""
    Analise os dados abaixo:

    {dados_empresa}

    Gere:

    1. Diagnóstico operacional
    2. Diagnóstico financeiro
    3. Avaliação do honorário
    4. Sugestão de preço
    5. Nota de A até D
    """

    resposta = model.generate_content(prompt)

    return resposta.text
