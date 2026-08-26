import html
import streamlit as st

def cabecalho_pagina(titulo, subtitulo="", kicker="Escrita Contabilidade"):
    subtitulo_html = (
        f'<div class="subtitulo">{html.escape(str(subtitulo))}</div>'
        if subtitulo else ''
    )

    st.markdown(
        f'''
        <div class="escrita-page-header">
            <div class="kicker">{html.escape(str(kicker))}</div>
            <div class="titulo">{html.escape(str(titulo))}</div>
            {subtitulo_html}
        </div>
        ''',
        unsafe_allow_html=True,
    )

def badge_status(status):
    status = str(status or "Em edição").strip()

    mapa = {
        "Em aberto": ("#FFF4D6", "#7A5A00"),
        "Em edição": ("#E9F0FF", "#234EA3"),
        "Proposta enviada": ("#E7F4FF", "#175CD3"),
        "Negociação": ("#F4EBFF", "#6941C6"),
        "Fechado": ("#E7F6EC", "#157A55"),
        "Contrato fechado": ("#E7F6EC", "#157A55"),
        "Perdido": ("#FDECEC", "#B42318"),
        "Arquivado": ("#F2F4F7", "#475467"),
    }

    fundo, cor = mapa.get(status, ("#F2F4F7", "#475467"))

    st.markdown(
        f'''
        <span style="
            display:inline-block;
            padding:6px 11px;
            border-radius:999px;
            background:{fundo};
            color:{cor};
            font-size:0.82rem;
            font-weight:800;
        ">
            {html.escape(status)}
        </span>
        ''',
        unsafe_allow_html=True,
    )
