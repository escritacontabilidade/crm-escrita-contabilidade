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

def aplicar_tema_escrita():
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
