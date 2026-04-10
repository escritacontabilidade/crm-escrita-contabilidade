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

    # Fontes mais estáveis no Streamlit/Linux
    fonte_regular_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    fonte_bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    fonte_oblique_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"
    fonte_bold_oblique_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf"

    try:
        fonte_titulo = ImageFont.truetype(fonte_bold_oblique_path, 56)
        fonte_subtitulo = ImageFont.truetype(fonte_regular_path, 34)
        fonte_valor = ImageFont.truetype(fonte_bold_path, 78)
        fonte_extenso = ImageFont.truetype(fonte_bold_oblique_path, 34)
        fonte_obs = ImageFont.truetype(fonte_regular_path, 18)
    except:
        fonte_titulo = ImageFont.load_default()
        fonte_subtitulo = ImageFont.load_default()
        fonte_valor = ImageFont.load_default()
        fonte_extenso = ImageFont.load_default()
        fonte_obs = ImageFont.load_default()

    azul = (7, 31, 66)
    dourado = (184, 153, 74)
    cinza = (80, 80, 80)
    branco = (255, 255, 255)

    valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    salario_minimo = 1518.00
    qtd_salarios = round(valor / salario_minimo, 2)
    texto_salario = f"o equivalente à {qtd_salarios} salários mínimos."

    valor_extenso = "(valor por extenso a ajustar)"

    observacao = (
        "*Além disso, será cobrado um honorário adicional em dezembro, no valor "
        "dos honorários vigentes, destinado à entrega das obrigações federais, "
        "estaduais, municipais e trabalhistas. Esse valor será devido "
        "proporcionalmente em rescisões de contrato."
    )

    # Caixa branca central baseada na arte
    caixa_x1, caixa_y1, caixa_x2, caixa_y2 = 250, 180, 1650, 1060
    draw.rounded_rectangle(
        (caixa_x1, caixa_y1, caixa_x2, caixa_y2),
        radius=55,
        fill=branco
    )

    caixa_centro_x = (caixa_x1 + caixa_x2) // 2

    def centralizar_texto(texto, fonte, y, cor):
        bbox = draw.textbbox((0, 0), texto, font=fonte)
        largura_texto = bbox[2] - bbox[0]
        x = caixa_centro_x - (largura_texto // 2)
        draw.text((x, y), texto, fill=cor, font=fonte)

    def quebrar_linhas_por_largura(texto, fonte, largura_max):
        palavras = texto.split()
        linhas = []
        atual = ""

        for palavra in palavras:
            teste = f"{atual} {palavra}".strip()
            bbox = draw.textbbox((0, 0), teste, font=fonte)
            largura_teste = bbox[2] - bbox[0]

            if largura_teste <= largura_max:
                atual = teste
            else:
                if atual:
                    linhas.append(atual)
                atual = palavra

        if atual:
            linhas.append(atual)

        return linhas

    # Título
    centralizar_texto("Honorários mensais para:", fonte_titulo, 255, dourado)
    centralizar_texto("contábil, fiscal, pessoal e societário.", fonte_subtitulo, 360, dourado)

    # Valor
    centralizar_texto(valor_formatado, fonte_valor, 500, azul)

    # Extenso
    centralizar_texto(valor_extenso, fonte_extenso, 650, azul)

    # Salários mínimos
    centralizar_texto(texto_salario, fonte_extenso, 715, azul)

    # Observação em múltiplas linhas centralizadas
    linhas_obs = quebrar_linhas_por_largura(
        observacao,
        fonte_obs,
        largura_max=980
    )

    y_obs = 860
    for linha in linhas_obs:
        bbox = draw.textbbox((0, 0), linha, font=fonte_obs)
        largura_linha = bbox[2] - bbox[0]
        x_obs = caixa_centro_x - (largura_linha // 2)
        draw.text((x_obs, y_obs), linha, fill=cinza, font=fonte_obs)
        y_obs += 28

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
