import os
import tempfile
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
import os

def gerar_lamina_preco(valor):
    # Caminho da imagem original
    caminho_base = "assets_proposta/10_preco.jpg"

    # Nova imagem gerada
    caminho_saida = "assets_proposta/10_preco_dinamico.jpg"

    # Abre a imagem base
    img = Image.open(caminho_base)
    draw = ImageDraw.Draw(img)

    # Tenta usar uma fonte melhor (se não tiver, usa padrão)
    try:
        fonte_valor = ImageFont.truetype("arial.ttf", 90)
        fonte_texto = ImageFont.truetype("arial.ttf", 35)
    except:
        fonte_valor = ImageFont.load_default()
        fonte_texto = ImageFont.load_default()

    # Valor formatado
    valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Texto por extenso (simples por enquanto)
    valor_extenso = "valor por extenso aqui"

    # Texto salário mínimo (ajustável depois)
    texto_salario = "equivalente a X salários mínimos"

    # POSIÇÕES (ajustaremos fino depois)
    draw.text((600, 450), valor_formatado, fill="black", font=fonte_valor)
    draw.text((600, 580), valor_extenso, fill="black", font=fonte_texto)
    draw.text((600, 650), texto_salario, fill="black", font=fonte_texto)

    # Salva nova imagem
    img.save(caminho_saida)

    return caminho_saida

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
