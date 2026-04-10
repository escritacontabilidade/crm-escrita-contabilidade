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

    # fontes
    try:
        fonte_valor = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(largura * 0.08))
        fonte_texto = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(largura * 0.025))
        fonte_obs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(largura * 0.018))
    except:
        fonte_valor = ImageFont.load_default()
        fonte_texto = ImageFont.load_default()
        fonte_obs = ImageFont.load_default()

    azul = (7, 31, 66)
    dourado = (184, 153, 74)
    cinza = (90, 90, 90)

    valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    salario_minimo = 1518.00
    qtd_salarios = round(valor / salario_minimo, 2)
    texto_salario = f"o equivalente a {qtd_salarios} salários mínimos."

    valor_extenso = "(valor por extenso a ajustar)"

    # centro horizontal
    centro_x = largura // 2

    def centralizar(texto, fonte, y, cor):
        bbox = draw.textbbox((0, 0), texto, font=fonte)
        w = bbox[2] - bbox[0]
        draw.text((centro_x - w // 2, y), texto, fill=cor, font=fonte)

    # POSIÇÕES BASEADAS NA ALTURA DA IMAGEM
    centralizar("Honorários mensais para:", fonte_texto, int(altura * 0.28), dourado)
    centralizar("contábil, fiscal, pessoal e societário.", fonte_texto, int(altura * 0.35), dourado)

    centralizar(valor_formatado, fonte_valor, int(altura * 0.48), azul)

    centralizar(valor_extenso, fonte_texto, int(altura * 0.63), azul)
    centralizar(texto_salario, fonte_texto, int(altura * 0.68), azul)

    observacao = (
        "*Além disso, será cobrado um honorário adicional em dezembro, no valor dos honorários vigentes, "
        "destinado à entrega das obrigações federais, estaduais, municipais e trabalhistas. "
        "Esse valor será devido proporcionalmente em rescisões de contrato."
    )

    # quebra por largura REAL
    max_width = int(largura * 0.7)

    palavras = observacao.split()
    linhas = []
    atual = ""

    for palavra in palavras:
        teste = f"{atual} {palavra}".strip()
        bbox = draw.textbbox((0, 0), teste, font=fonte_obs)
        if bbox[2] <= max_width:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra

    if atual:
        linhas.append(atual)

    y = int(altura * 0.78)

    for linha in linhas:
        bbox = draw.textbbox((0, 0), linha, font=fonte_obs)
        w = bbox[2]
        draw.text((centro_x - w // 2, y), linha, fill=cinza, font=fonte_obs)
        y += int(altura * 0.035)

    img.save(caminho_saida, quality=95)
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
