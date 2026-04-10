import os
import tempfile
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
import os

def gerar_lamina_preco(valor):
    caminho_base = "assets_proposta/10_preco.jpg"
    caminho_saida = "assets_proposta/10_preco_dinamico.jpg"

    img = Image.open(caminho_base).convert("RGB")
    draw = ImageDraw.Draw(img)
    largura, altura = img.size

    # Fonte do valor
    try:
        fonte_valor = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            int(largura * 0.11)
        )
    except:
        fonte_valor = ImageFont.load_default()

    azul = (7, 31, 66)
    branco = (255, 255, 255)

    valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # 1) Apaga só a área do valor antigo
    x1 = int(largura * 0.32)
    y1 = int(altura * 0.43)
    x2 = int(largura * 0.68)
    y2 = int(altura * 0.58)

    draw.rectangle((x1, y1, x2, y2), fill=branco)

    # 2) Centraliza o valor novo
    bbox = draw.textbbox((0, 0), valor_formatado, font=fonte_valor)
    largura_texto = bbox[2] - bbox[0]
    altura_texto = bbox[3] - bbox[1]

    x_texto = (largura - largura_texto) // 2
    y_texto = int(altura * 0.455)

    draw.text((x_texto, y_texto), valor_formatado, fill=azul, font=fonte_valor)
    
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


def gerar_pdf(dados=None, mensal=0, extras_df=None):
    temp_dir = tempfile.gettempdir()
    caminho_pdf = os.path.join(temp_dir, "proposta_simples.pdf")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Proposta", ln=True)

    if dados:
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Cliente: {dados.get('nome', dados.get('cliente', ''))}", ln=True)

    pdf.cell(0, 10, f"Valor mensal: R$ {mensal}", ln=True)
    pdf.output(caminho_pdf)
    return caminho_pdf


def moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_pdf_proposta_comercial(nome_empresa, segmento, plano, valor_mensal):
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)

    lamina_preco = gerar_lamina_preco(valor_mensal)

    for caminho in IMAGENS_PROPOSTA:
        caminho_usado = caminho

        if caminho == "assets_proposta/10_preco.jpg":
            caminho_usado = lamina_preco

        if os.path.exists(caminho_usado):
            pdf.add_page()
            pdf.image(caminho_usado, x=0, y=0, w=297, h=210)

    temp_dir = tempfile.gettempdir()
    nome_limpo = "".join(c for c in nome_empresa if c.isalnum() or c in (" ", "_", "-")).strip()
    if not nome_limpo:
        nome_limpo = "proposta"

    nome_arquivo = f"proposta_{nome_limpo.replace(' ', '_')}.pdf"
    caminho_pdf = os.path.join(temp_dir, nome_arquivo)

    pdf.output(caminho_pdf)
    return caminho_pdf
