"""Conexão financeira do CRM Escrita: leitura admin/comercial; gravação admin."""
import streamlit as st
from supabase import create_client


def exigir_acesso_honorarios():
    if (st.session_state.get('autenticado') is not True or
            st.session_state.get('perfil_usuario') not in ('admin', 'comercial')):
        raise PermissionError('Acesso aos honorários não autorizado.')


def exigir_admin():
    exigir_acesso_honorarios()
    if st.session_state.get('perfil_usuario') != 'admin':
        raise PermissionError('Alterações financeiras são exclusivas do administrador.')


def get_supabase_financeiro():
    """Chave privilegiada utilizada exclusivamente no servidor Streamlit."""
    exigir_acesso_honorarios()
    return create_client(st.secrets['SUPABASE_URL'], st.secrets['SUPABASE_SECRET_KEY'])


def get_supabase_admin():
    """Compatibilidade com código administrativo já existente."""
    exigir_admin()
    return get_supabase_financeiro()
