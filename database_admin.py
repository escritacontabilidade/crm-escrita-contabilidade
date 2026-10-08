import streamlit as st
from supabase import create_client


def exigir_admin():
    """Impede acesso às operações financeiras sem login administrativo."""
    if (
        st.session_state.get("autenticado") is not True
        or st.session_state.get("perfil_usuario") != "admin"
    ):
        raise PermissionError(
            "Acesso negado. Esta funcionalidade é exclusiva do administrador."
        )


def get_supabase_admin():
    """Cria uma conexão privilegiada somente após validar o administrador."""
    exigir_admin()

    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SECRET_KEY"]

    return create_client(url, key)
