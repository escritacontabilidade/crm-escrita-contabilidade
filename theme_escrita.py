"""Identidade visual do CRM Escrita. Alterações exclusivamente de apresentação."""

import streamlit as st

CORES = {
    "azul_900": "#081B2C",
    "azul_800": "#102D4A",
    "azul_700": "#183E63",
    "dourado": "#B79A45",
    "dourado_claro": "#D7C27A",
    "fundo": "#F5F7FA",
    "card": "#FFFFFF",
    "texto": "#182230",
    "texto_secundario": "#667085",
    "borda": "#E4E7EC",
}

def _aplicar_tema_publico():
    st.markdown(
        f"""
        <style>
        :root {{
            --escrita-azul-900: {CORES["azul_900"]};
            --escrita-azul-800: {CORES["azul_800"]};
            --escrita-azul-700: {CORES["azul_700"]};
            --escrita-dourado: {CORES["dourado"]};
            --escrita-dourado-claro: {CORES["dourado_claro"]};
            --escrita-fundo: {CORES["fundo"]};
            --escrita-card: {CORES["card"]};
            --escrita-texto: {CORES["texto"]};
            --escrita-texto-secundario: {CORES["texto_secundario"]};
            --escrita-borda: {CORES["borda"]};
        }}

        .stApp {{
            background: var(--escrita-fundo);
        }}

        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #FFFFFF 0%, #F7F9FC 100%);
            border-right: 1px solid var(--escrita-borda);
        }}

        h1, h2, h3 {{
            color: var(--escrita-azul-900) !important;
            letter-spacing: -0.02em;
        }}

        h1 {{
            font-weight: 800 !important;
        }}

        h2, h3 {{
            font-weight: 700 !important;
        }}

        .block-container {{
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1480px;
        }}

        div[data-testid="stMetric"] {{
            background: #FFFFFF;
            border: 1px solid var(--escrita-borda);
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 5px 20px rgba(8, 27, 44, 0.05);
        }}

        div[data-testid="stMetric"] label {{
            color: var(--escrita-texto-secundario);
            font-weight: 600;
        }}

        div[data-testid="stMetricValue"] {{
            color: var(--escrita-azul-900);
            font-weight: 800;
        }}

        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stTextArea"] textarea {{
            border-radius: 10px !important;
            border-color: var(--escrita-borda) !important;
            background: #FFFFFF !important;
        }}

        div[data-baseweb="select"] > div {{
            border-radius: 10px !important;
            border-color: var(--escrita-borda) !important;
            background: #FFFFFF !important;
        }}

        div.stButton > button,
        div.stDownloadButton > button {{
            border-radius: 10px !important;
            min-height: 42px;
            font-weight: 700 !important;
            border: 1px solid var(--escrita-azul-700) !important;
        }}

        div.stButton > button:hover,
        div.stDownloadButton > button:hover {{
            border-color: var(--escrita-dourado) !important;
        }}

        div[data-testid="stForm"] {{
            background: #FFFFFF;
            border: 1px solid var(--escrita-borda);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 5px 20px rgba(8, 27, 44, 0.04);
        }}

        div[data-testid="stExpander"] {{
            border: 1px solid var(--escrita-borda);
            border-radius: 12px;
            background: #FFFFFF;
        }}

        div[data-testid="stDataFrame"] {{
            border: 1px solid var(--escrita-borda);
            border-radius: 14px;
            overflow: hidden;
            background: #FFFFFF;
        }}

        hr {{
            border-color: var(--escrita-borda) !important;
        }}

        .metric-card {{
            background: linear-gradient(135deg, var(--escrita-azul-900), var(--escrita-azul-700));
            padding: 24px;
            border-radius: 16px;
            color: #FFFFFF;
            text-align: left;
            border: 1px solid rgba(183, 154, 69, 0.65);
            box-shadow: 0 8px 24px rgba(8, 27, 44, 0.14);
        }}

        .metric-card p {{
            margin: 0;
            color: #E9EEF5 !important;
            font-size: 0.9rem;
            font-weight: 700;
            letter-spacing: 0.04em;
        }}

        .metric-card h2 {{
            color: var(--escrita-dourado-claro) !important;
            margin: 8px 0 0 0 !important;
        }}

        .escrita-page-header {{
            background: linear-gradient(135deg, var(--escrita-azul-900) 0%, var(--escrita-azul-700) 100%);
            border-radius: 20px;
            padding: 26px 30px;
            color: #FFFFFF;
            margin-bottom: 22px;
            box-shadow: 0 10px 30px rgba(8, 27, 44, 0.14);
            border: 1px solid rgba(183, 154, 69, 0.45);
        }}

        .escrita-page-header .kicker {{
            color: var(--escrita-dourado-claro);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            margin-bottom: 6px;
        }}

        .escrita-page-header .titulo {{
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.1;
            margin: 0;
        }}

        .escrita-page-header .subtitulo {{
            margin-top: 8px;
            color: #DCE6F0;
            font-size: 0.98rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def aplicar_tema_escrita():
    """Aplica o tema interno e mantém o tema anterior nos links públicos."""
    if st.query_params.get("modo") in {
        "cliente", "site", "cliente_radar", "constituicao"
    }:
        _aplicar_tema_publico()
        return

    st.markdown(
        """
        <style>
        :root {
            --escrita-azul-900: #102B45;
            --escrita-azul-800: #17456D;
            --escrita-azul-700: #1D5D91;
            --escrita-dourado: #A98D38;
            --escrita-dourado-claro: #D7C27A;
            --escrita-fundo: #F5F6FA;
            --escrita-card: #FFFFFF;
            --escrita-texto: #202C3B;
            --escrita-texto-secundario: #657487;
            --escrita-borda: #E3E8EF;
        }

        .stApp, [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background: var(--escrita-fundo);
            color: var(--escrita-texto);
            color-scheme: light;
            font-family: "Segoe UI", Arial, sans-serif;
        }
        [data-testid="stHeader"] {
            background: #FFFFFF;
            border-bottom: 1px solid var(--escrita-borda);
        }
        [data-testid="stHeader"] button {
            color: var(--escrita-azul-900);
        }
        [data-testid="stMainBlockContainer"],
        [data-testid="stMain"] .block-container {
            max-width: 1560px;
            padding: 2rem 2rem 3rem;
        }
        [data-testid="stMain"] h1,
        [data-testid="stMain"] h2,
        [data-testid="stMain"] h3 {
            color: var(--escrita-azul-900);
            font-weight: 700;
            letter-spacing: -0.025em;
        }
        [data-testid="stMain"] h1 { font-size: 1.8rem; }
        [data-testid="stMain"] h2 { font-size: 1.35rem; }
        [data-testid="stMain"] h3 { font-size: 1.1rem; }
        [data-testid="stMain"] [data-testid="stWidgetLabel"] p {
            color: var(--escrita-texto);
            font-size: .88rem;
            font-weight: 600;
        }
        [data-testid="stMain"] [data-testid="stCaptionContainer"] {
            color: var(--escrita-texto-secundario);
        }
        [data-testid="stMain"] hr {
            border-color: var(--escrita-borda);
            margin: 1.2rem 0;
        }

        /* Sidebar: mantém os controles e a navegação existentes. */
        [data-testid="stSidebar"] {
            background: #10171F;
            color: #E7EDF4;
            border-right: 1px solid #243241;
            color-scheme: dark;
        }
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            background: #10171F;
        }
        [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
            padding: 1.5rem 1.1rem;
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
            color: #E7EDF4;
        }
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            color: #AFBDCB;
        }
        /* A marca colorida original permanece legível sobre branco. */
        [data-testid="stSidebar"] [data-testid="stImage"] {
            background: #FFFFFF;
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 1.2rem;
            box-sizing: border-box;
        }
        [data-testid="stSidebar"] [data-testid="stImage"] img {
            max-width: 100%;
            height: auto;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] > div {
            background: #1B2B3C !important;
            color: #FFFFFF !important;
            border-color: #365068 !important;
            border-radius: 6px;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] span,
        [data-testid="stSidebar"] [data-baseweb="select"] svg {
            color: #FFFFFF;
            fill: currentColor;
        }
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea {
            color: #FFFFFF;
            background: #1B2B3C;
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button {
            background: #18232F;
            color: #E7EDF4;
            border: 1px solid #344356;
            border-radius: 6px;
            width: 100%;
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button:hover {
            background: #233B51;
            border-color: #A98D38;
        }
        [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button {
            color: #E7EDF4;
        }
        [data-testid="stSidebar"] hr { border-color: #344356; }

        /* Indicadores, formulários e tabelas. */
        [data-testid="stMain"] [data-testid="stMetric"] {
            background: #FFFFFF;
            border: 1px solid var(--escrita-borda);
            border-top: 3px solid var(--escrita-azul-700);
            border-radius: 8px;
            padding: 16px 18px;
            box-shadow: none;
        }
        [data-testid="stMain"] [data-testid="stMetricLabel"] {
            color: var(--escrita-texto-secundario);
            font-weight: 600;
        }
        [data-testid="stMain"] [data-testid="stMetricValue"] {
            color: var(--escrita-azul-900);
            font-weight: 700;
            font-size: 1.75rem;
        }
        [data-testid="stMain"] [data-testid="stForm"] {
            background: #FFFFFF;
            border: 1px solid var(--escrita-borda);
            border-radius: 8px;
            padding: 20px;
            box-shadow: none;
        }
        [data-testid="stMain"] [data-testid="stExpander"] {
            background: #FFFFFF;
            border: 1px solid var(--escrita-borda);
            border-radius: 8px;
        }
        [data-testid="stMain"] [data-testid="stExpander"] details,
        [data-testid="stMain"] [data-testid="stExpander"] summary {
            background: #FFFFFF;
            color: var(--escrita-texto);
            border-radius: 8px;
        }
        [data-testid="stMain"] [data-testid="stDataFrame"],
        [data-testid="stMain"] [data-testid="stTable"] {
            border: 1px solid var(--escrita-borda);
            border-radius: 8px;
            overflow: hidden;
            background: #FFFFFF;
        }
        [data-testid="stMain"] [data-testid="stTable"] th {
            background: #EDF2F7;
            color: var(--escrita-azul-900);
            font-weight: 600;
        }
        [data-testid="stMain"] [data-testid="stTable"] td {
            color: var(--escrita-texto);
            border-color: var(--escrita-borda);
        }

        /* Campos claros mesmo quando o navegador usa modo escuro. */
        [data-testid="stMain"] [data-baseweb="input"],
        [data-testid="stMain"] [data-baseweb="input"] > div,
        [data-testid="stMain"] [data-baseweb="textarea"],
        [data-testid="stMain"] [data-baseweb="select"] > div {
            background: #FFFFFF !important;
            color: var(--escrita-texto) !important;
            border-color: #CDD6E0 !important;
            border-radius: 6px;
        }
        [data-testid="stMain"] input,
        [data-testid="stMain"] textarea {
            color: var(--escrita-texto) !important;
            -webkit-text-fill-color: var(--escrita-texto) !important;
            caret-color: var(--escrita-azul-700);
        }
        [data-testid="stMain"] input::placeholder,
        [data-testid="stMain"] textarea::placeholder {
            -webkit-text-fill-color: #7B8797 !important;
            color: #7B8797 !important;
        }
        [data-testid="stMain"] [data-baseweb="select"] svg {
            color: var(--escrita-texto-secundario);
            fill: currentColor;
        }
        [data-testid="stMain"] [data-baseweb="select"] [data-baseweb="tag"] {
            background: #E8F0F8;
            color: var(--escrita-azul-900);
        }
        [data-testid="stMain"] [data-testid="stFileUploaderDropzone"] {
            background: #F8FAFC;
            color: var(--escrita-texto);
            border: 1px dashed #A9BACB;
            border-radius: 8px;
        }

        [data-testid="stMain"] [data-testid="stButton"] button,
        [data-testid="stMain"] [data-testid="stDownloadButton"] button,
        [data-testid="stMain"] [data-testid="stFormSubmitButton"] button {
            background: #FFFFFF;
            color: var(--escrita-azul-700);
            border: 1px solid #BDCCDA;
            border-radius: 6px;
            min-height: 40px;
            font-weight: 600;
            box-shadow: none;
        }
        [data-testid="stMain"] button[kind="primary"],
        [data-testid="stMain"] button[kind="primaryFormSubmit"] {
            background: var(--escrita-azul-700);
            color: #FFFFFF;
            border-color: var(--escrita-azul-700);
        }
        [data-testid="stMain"] [data-testid="stButton"] button:hover:not(:disabled),
        [data-testid="stMain"] [data-testid="stDownloadButton"] button:hover:not(:disabled),
        [data-testid="stMain"] [data-testid="stFormSubmitButton"] button:hover:not(:disabled) {
            border-color: var(--escrita-azul-700);
            background: #EAF1F8;
            color: var(--escrita-azul-900);
        }
        [data-testid="stMain"] button:disabled { opacity: .5; }
        [data-testid="stMain"] button:focus-visible,
        [data-testid="stSidebar"] button:focus-visible {
            outline: 2px solid var(--escrita-dourado);
            outline-offset: 2px;
        }
        [data-testid="stMain"] [data-baseweb="tab-list"] {
            background: transparent;
            border-bottom: 1px solid var(--escrita-borda);
            gap: 8px;
        }
        [data-testid="stMain"] [data-baseweb="tab"] {
            color: var(--escrita-texto-secundario);
            border-radius: 6px 6px 0 0;
            font-weight: 600;
        }
        [data-testid="stMain"] [data-baseweb="tab"][aria-selected="true"] {
            background: #E8F0F8;
            color: var(--escrita-azul-700);
        }
        [data-testid="stMain"] [data-baseweb="tab-highlight"] {
            background: var(--escrita-azul-700);
        }

        /* Classes já utilizadas pelo app.py e pelo ui_escrita.py. */
        .metric-card {
            background: #FFFFFF;
            border: 1px solid var(--escrita-borda);
            border-top: 3px solid var(--escrita-dourado);
            border-radius: 8px;
            padding: 18px 20px;
            color: var(--escrita-texto);
            text-align: left;
            box-shadow: none;
        }
        .metric-card p {
            margin: 0;
            color: var(--escrita-texto-secundario);
            font-size: .85rem;
            font-weight: 600;
            letter-spacing: .025em;
        }
        [data-testid="stMain"] .metric-card h2 {
            color: var(--escrita-azul-700);
            margin: 8px 0 0;
            font-size: 1.6rem;
        }
        .escrita-page-header {
            background: #FFFFFF;
            border: 1px solid var(--escrita-borda);
            border-left: 4px solid var(--escrita-dourado);
            border-radius: 6px;
            padding: 18px 22px;
            margin-bottom: 20px;
            color: var(--escrita-azul-900);
            box-shadow: none;
        }
        .escrita-page-header .kicker {
            color: #806923;
            font-size: .72rem;
            font-weight: 700;
            letter-spacing: .12em;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        .escrita-page-header .titulo {
            color: var(--escrita-azul-900);
            font-size: 1.65rem;
            font-weight: 700;
            line-height: 1.25;
        }
        .escrita-page-header .subtitulo {
            margin-top: 6px;
            color: var(--escrita-texto-secundario);
            font-size: .92rem;
            line-height: 1.5;
        }
        @media (max-width: 768px) {
            [data-testid="stMainBlockContainer"],
            [data-testid="stMain"] .block-container {
                padding: 1.25rem 1rem 2rem;
            }
            .escrita-page-header { padding: 15px 16px; }
            .escrita-page-header .titulo { font-size: 1.35rem; }
            [data-testid="stMain"] h1 { font-size: 1.5rem; }
            .metric-card { padding: 15px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
