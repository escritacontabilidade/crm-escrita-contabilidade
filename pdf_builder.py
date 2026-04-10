import os
import tempfile
from fpdf import FPDF


IMAGENS_PROPOSTA = [
    "assets_proposta/01_capa.jpg",
    "assets_proposta/02_autoridade.jpg",
    "assets_proposta/03_lideranca.jpg",
    "assets_proposta/04_rodrigo.jpg",
    "assets_proposta/05_roberta.jpg",
    "assets_proposta/06_simone.jpg",
    "assets_proposta/07_diferenciais.jpg",
    "assets_proposta/08_servicos.jpg",
    "assets_proposta/09_sistemas.jpg",
    "assets_proposta/10_preco.jpg",
    "assets_proposta/11_obrigacoes.jpg",
    "assets_proposta/12_extras_1.jpg",
    "assets_proposta/13_extras_2.jpg",
]


def moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_pdf_proposta_comercial(nome_empresa, segmento, plano, valor_mensal):
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)

    # 1) páginas com imagens
    for caminho in IMAGENS_PROPOSTA:
        if os.path.exists(caminho):
            pdf.add_page()
            pdf.image(caminho, x=0, y=0, w=297, h=210)

    # 2) página final dinâmica
    pdf.add_page()
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(0, 0, 297, 210, "F")

    pdf.set_text_color(15, 32, 58)

    pdf.set_xy(15, 20)
    pdf.set_font("Arial", "B", 26)
    pdf.cell(0, 12, "Resumo da Proposta Comercial", ln=True)

    pdf.ln(8)
    pdf.set_font("Arial", "", 18)
    pdf.cell(0, 10, f"Empresa: {nome_empresa}", ln=True)
    pdf.cell(0, 10, f"Segmento: {segmento}", ln=True)
    pdf.cell(0, 10, f"Plano apresentado: {plano}", ln=True)

    pdf.ln(12)
    pdf.set_font("Arial", "B", 34)
    pdf.cell(0, 16, moeda_br(valor_mensal), ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", "", 16)
    texto1 = (
        "Honorario mensal para prestacao de servicos contabil, fiscal, pessoal e societario."
    )
    texto2 = (
        "Observacao: alem disso, sera cobrado um honorario adicional em dezembro, "
        "no valor dos honorarios vigentes, destinado a entrega das obrigacoes federais, "
        "estaduais, municipais e trabalhistas. Esse valor sera devido proporcionalmente "
        "em rescisoes de contrato."
    )

    pdf.multi_cell(0, 10, texto1)
    pdf.ln(4)
    pdf.multi_cell(0, 9, texto2)

    # 3) salvar em arquivo temporário
    temp_dir = tempfile.gettempdir()
    nome_limpo = "".join(c for c in nome_empresa if c.isalnum() or c in (" ", "_", "-")).strip()
    if not nome_limpo:
        nome_limpo = "proposta"
    nome_arquivo = f"proposta_{nome_limpo.replace(' ', '_')}.pdf"
    caminho_pdf = os.path.join(temp_dir, nome_arquivo)

    pdf.output(caminho_pdf)
    return caminho_pdf
