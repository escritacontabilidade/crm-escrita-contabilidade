import io
import pandas as pd
import streamlit as st


def buscar_tabela(supabase, nome_tabela):
    try:
        res = supabase.table(nome_tabela).select("*").execute()
        return pd.DataFrame(res.data or [])
    except Exception as e:
        return pd.DataFrame([{
            "erro": f"Erro ao buscar {nome_tabela}: {e}"
        }])


def montar_regras_especiais_python():
    return pd.DataFrame([
        {
            "regra": "Conciliação bancária",
            "condição": "Se a empresa NÃO faz conciliação bancária",
            "fórmula": "Quantidade de contas bancárias x R$ 500,00",
            "origem": "pricing.py"
        },
        {
            "regra": "Agente de Carga - processos por mês",
            "condição": "Até 100 processos",
            "fórmula": "Quantidade de processos x R$ 50,00",
            "origem": "pricing.py"
        },
        {
            "regra": "Agente de Carga - processos por mês",
            "condição": "De 101 até 500 processos",
            "fórmula": "Quantidade de processos x R$ 40,00",
            "origem": "pricing.py"
        },
        {
            "regra": "Agente de Carga - processos por mês",
            "condição": "Acima de 500 processos",
            "fórmula": "Quantidade de processos x R$ 30,00",
            "origem": "pricing.py"
        },
        {
            "regra": "Despachante Aduaneiro - processos por mês",
            "condição": "Até 100 processos",
            "fórmula": "Quantidade de processos x R$ 30,00",
            "origem": "pricing.py"
        },
        {
            "regra": "Despachante Aduaneiro - processos por mês",
            "condição": "De 101 até 500 processos",
            "fórmula": "Quantidade de processos x R$ 25,00",
            "origem": "pricing.py"
        },
        {
            "regra": "Despachante Aduaneiro - processos por mês",
            "condição": "Acima de 500 processos",
            "fórmula": "Quantidade de processos x R$ 20,00",
            "origem": "pricing.py"
        },
    ])


def montar_formula_final():
    return pd.DataFrame([
        {
            "etapa": "1. Seleção de segmento",
            "descrição": "Usuário escolhe o segmento no CRM.",
            "origem": "app.py"
        },
        {
            "etapa": "2. Origem das perguntas",
            "descrição": "Sistema consulta regras_segmento para identificar qual origem de perguntas será usada.",
            "origem": "Supabase / regras_segmento"
        },
        {
            "etapa": "3. Preço base",
            "descrição": "Sistema consulta precos_base_precificacao conforme tabela_base, regime tributário e faixa de faturamento.",
            "origem": "Supabase / precos_base_precificacao"
        },
        {
            "etapa": "4. Acréscimos",
            "descrição": "Sistema calcula acréscimos conforme respostas do questionário e regras_perguntas_precificacao.",
            "origem": "Supabase / regras_perguntas_precificacao"
        },
        {
            "etapa": "5. Regras especiais",
            "descrição": "Sistema aplica regras especiais fixas em código, como conciliação bancária e processos por faixa.",
            "origem": "pricing.py"
        },
        {
            "etapa": "6. Bronze",
            "descrição": "Bronze = preço base calculado.",
            "origem": "app.py"
        },
        {
            "etapa": "7. Prata",
            "descrição": "Prata = preço base calculado x 1,15.",
            "origem": "app.py"
        },
        {
            "etapa": "8. Ouro",
            "descrição": "Ouro = preço base calculado x 1,35.",
            "origem": "app.py"
        },
    ])


def gerar_excel_matriz_precificacao(supabase):
    tabelas = {
        "Configuracoes": buscar_tabela(supabase, "configuracao_operacional"),
        "Pesos_Esforco": buscar_tabela(supabase, "pesos_esforco"),
        "Segmentos": buscar_tabela(supabase, "segmentos"),
        "Regras_Segmento": buscar_tabela(supabase, "regras_segmento"),
        "Perguntas": buscar_tabela(supabase, "perguntas"),
        "Precos_Base": buscar_tabela(supabase, "precos_base_precificacao"),
        "Regras_Perguntas": buscar_tabela(supabase, "regras_perguntas_precificacao"),
        "Regras_Especiais": montar_regras_especiais_python(),
        "Formula_Final": montar_formula_final(),
    }

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for nome_aba, df in tabelas.items():
            df.to_excel(writer, sheet_name=nome_aba[:31], index=False)

    output.seek(0)
    return output


def tela_exportar_matriz_precificacao(supabase):
    st.title("📊 Matriz de Precificação")
    st.info("Exporta toda a lógica comercial da precificação para Excel: tabelas, perguntas, regras, faixas, pesos e fórmulas especiais.")

    if st.button("Gerar Matriz de Precificação em Excel"):
        try:
            arquivo_excel = gerar_excel_matriz_precificacao(supabase)

            st.success("Matriz gerada com sucesso.")

            st.download_button(
                label="⬇️ Baixar Matriz de Precificação",
                data=arquivo_excel,
                file_name="Matriz_Precificacao_Escrita_Contabilidade.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"Erro ao gerar matriz de precificação: {e}")
