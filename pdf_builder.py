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

    # tenta fontes comuns do Linux/Streamlit
    caminhos_fontes = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    fonte_valor = None
    fonte_extenso = None
    fonte_obs = None

    for caminho_fonte in caminhos_fontes:
        if os.path.exists(caminho_fonte):
            try:
                fonte_valor = ImageFont.truetype(caminho_fonte, 110)
                fonte_extenso = ImageFont.truetype(caminho_fonte, 36)
                fonte_obs = ImageFont.truetype(caminho_fonte, 24)
                break
            except:
                pass

    if fonte_valor is None:
        fonte_valor = ImageFont.load_default()
        fonte_extenso = ImageFont.load_default()
        fonte_obs = ImageFont.load_default()

    valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    salario_minimo = 1518.00
    qtd_salarios = round(valor / salario_minimo, 2)
    texto_salario = f"o equivalente a {qtd_salarios} salários mínimos."

    valor_extenso = "(valor por extenso a ajustar)"

    # apaga a área antiga
    draw.rounded_rectangle((430, 250, 1450, 1030), radius=40, fill=(255, 255, 255))

    # título
    draw.text((560, 320), "Honorários mensais para:", fill=(184, 153, 74), font=fonte_extenso)
    draw.text((720, 395), "contábil, fiscal, pessoal e societário.", fill=(184, 153, 74), font=fonte_extenso)

    # valor principal
    draw.text((700, 520), valor_formatado, fill=(7, 31, 66), font=fonte_valor)

    # extenso
    draw.text((610, 680), valor_extenso, fill=(7, 31, 66), font=fonte_extenso)

    # salários mínimos
    draw.text((690, 740), texto_salario, fill=(7, 31, 66), font=fonte_extenso)

    # observação
    observacao = (
        "*Além disso, será cobrado um honorário adicional em dezembro, no valor "
        "dos honorários vigentes, destinado à entrega das obrigações federais, "
        "estaduais, municipais e trabalhistas. Esse valor será devido "
        "proporcionalmente em rescisões de contrato."
    )

    # quebra simples em linhas
    largura_max = 90
    palavras = observacao.split()
    linhas = []
    linha_atual = ""

    for palavra in palavras:
        teste = f"{linha_atual} {palavra}".strip()
        if len(teste) <= largura_max:
            linha_atual = teste
        else:
            linhas.append(linha_atual)
            linha_atual = palavra

    if linha_atual:
        linhas.append(linha_atual)

    y = 850
    for linha in linhas:
        draw.text((520, y), linha, fill=(70, 70, 70), font=fonte_obs)
        y += 30

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
