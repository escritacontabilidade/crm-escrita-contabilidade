import pandas as pd
import streamlit as st


def tela_grupos_economicos(supabase):
    st.title("🏢 Grupos Econômicos")
    st.info("Cadastro opcional para organizar matriz, filiais e empresas relacionadas. Não bloqueia o fluxo de leads ou propostas.")

    st.subheader("Cadastrar novo grupo")

    with st.form("form_novo_grupo"):
        nome_grupo = st.text_input("Nome do grupo econômico")
        observacoes = st.text_area("Observações")

        salvar = st.form_submit_button("Salvar grupo")

        if salvar:
            if not nome_grupo:
                st.warning("Informe o nome do grupo econômico.")
                st.stop()

            try:
                supabase.table("grupos_economicos").insert({
                    "nome_grupo": nome_grupo,
                    "observacoes": observacoes,
                    "ativo": True
                }).execute()

                st.success("Grupo econômico cadastrado com sucesso.")
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao salvar grupo econômico: {e}")

    st.divider()
    st.subheader("Grupos cadastrados")

    try:
        res = supabase.table("grupos_economicos") \
            .select("*") \
            .eq("ativo", True) \
            .order("nome_grupo") \
            .execute()

        if not res.data:
            st.info("Nenhum grupo econômico cadastrado ainda.")
            return

        df = pd.DataFrame(res.data)

        colunas = ["id", "nome_grupo", "observacoes", "created_at"]
        colunas = [c for c in colunas if c in df.columns]

        st.dataframe(df[colunas], use_container_width=True)

        opcoes = [
            f"{row['id']} | {row.get('nome_grupo', '')}"
            for _, row in df.iterrows()
        ]

        grupo_escolhido = st.selectbox("Selecione um grupo para editar", opcoes)

        grupo_id = int(grupo_escolhido.split("|")[0].strip())
        grupo = df[df["id"] == grupo_id].iloc[0].to_dict()

        st.divider()
        st.subheader("Editar grupo")

        with st.form("form_editar_grupo"):
            novo_nome = st.text_input("Nome do grupo", value=grupo.get("nome_grupo") or "")
            novas_observacoes = st.text_area("Observações", value=grupo.get("observacoes") or "")

            col1, col2 = st.columns(2)

            with col1:
                salvar_edicao = st.form_submit_button("Salvar alterações")

            with col2:
                arquivar = st.form_submit_button("Arquivar grupo")

            if salvar_edicao:
                if not novo_nome:
                    st.warning("Informe o nome do grupo.")
                    st.stop()

                supabase.table("grupos_economicos").update({
                    "nome_grupo": novo_nome,
                    "observacoes": novas_observacoes,
                    "updated_at": pd.Timestamp.now().isoformat()
                }).eq("id", grupo_id).execute()

                st.success("Grupo atualizado com sucesso.")
                st.rerun()

            if arquivar:
                supabase.table("grupos_economicos").update({
                    "ativo": False,
                    "updated_at": pd.Timestamp.now().isoformat()
                }).eq("id", grupo_id).execute()

                st.success("Grupo arquivado com sucesso.")
                st.rerun()

    except Exception as e:
        st.error(f"Erro ao carregar grupos econômicos: {e}")
