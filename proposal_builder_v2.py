import os
import textwrap
import tempfile
from datetime import datetime
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont


ASSETS_DIR = "assets_proposta_v2"
PAGE_W, PAGE_H = 1920, 1080


SERVICOS_TEXTOS = {
    "Contábil": [
        "Elaboração da Contabilidade, de acordo com as Normas Brasileiras de Contabilidade.",
        "Emissão de balancetes e DRE (Demonstração do Resultado do Exercício).",
        "Envio de obrigações acessórias mensais, como SPED Contábil, DCTF e demais demonstrações contábeis obrigatórias."
    ],
    "Fiscal": [
        "Escrituração dos registros fiscais obrigatórios eletrônicos.",
        "Elaboração de guias de contribuições e tributos referentes às operações de compra, venda e prestação de serviços realizadas pela empresa.",
        "Orientação relativa à tributação das operações da empresa.",
        "Envio de informações de obrigações acessórias mensais, como SPED Fiscal, SPED Contribuições, EFD Reinf e FISS."
    ],
    "Pessoal": [
        "Orientação e controle da aplicação das normas da CLT e convenções coletivas.",
        "Elaboração de férias, adiantamento salarial, rescisões contratuais e manutenção dos registros dos empregados.",
        "Envio dos arquivos relacionados ao eSocial, observando os prazos legais.",
        "Elaboração da folha de pagamento e guias de recolhimento dos encargos sociais, tributários e obrigações acessórias."
    ],
    "Societário": [
        "Controle e renovação dos alvarás de funcionamento, bombeiro e sanitário.",
        "Emissão de certidões negativas da empresa, disponíveis de forma online.",
        "Acompanhamento de alterações cadastrais e societárias conforme necessidade da empresa."
    ],
}


def _font(size=32, bold=False, italic=False):
    try:
        if bold:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        if italic:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf", size)
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def _formatar_moeda(valor):
    try:
        valor = float(valor or 0)
    except Exception:
        valor = 0.0
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _quebrar_texto(texto, fonte, largura_max, draw):
    palavras = str(texto).split()
    linhas = []
    linha = ""

    for palavra in palavras:
        teste = (linha + " " + palavra).strip()
        bbox = draw.textbbox((0, 0), teste, font=fonte)
        if bbox[2] - bbox[0] <= largura_max:
            linha = teste
        else:
            if linha:
                linhas.append(linha)
            linha = palavra

    if linha:
        linhas.append(linha)

    return linhas


def _texto_centralizado(draw, texto, caixa, fonte, fill):
    x1, y1, x2, y2 = caixa
    linhas = _quebrar_texto(texto, fonte, x2 - x1, draw)

    altura_linha = fonte.size + 8
    altura_total = len(linhas) * altura_linha
    y = y1 + ((y2 - y1 - altura_total) / 2)

    for linha in linhas:
        bbox = draw.textbbox((0, 0), linha, font=fonte)
        largura = bbox[2] - bbox[0]
        x = x1 + ((x2 - x1 - largura) / 2)
        draw.text((x, y), linha, font=fonte, fill=fill)
        y += altura_linha


def _salvar_temp(img, prefixo):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png", prefix=prefixo)
    img.save(tmp.name)
    return tmp.name


def _abrir_slide(numero):
    caminho = os.path.join(ASSETS_DIR, f"{numero}.png")
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Slide não encontrado: {caminho}")

    img = Image.open(caminho).convert("RGB")
    return img.resize((PAGE_W, PAGE_H))


def _slide_capa(nome_empresa):
    img = _abrir_slide(1)
    draw = ImageDraw.Draw(img)

    fonte = _font(30)
    fill = (255, 255, 255)

    # Caixa azul da capa onde estava "Nome da empresa"
    caixa = (520, 690, 1080, 765)

    _texto_centralizado(draw, nome_empresa or "Nome da empresa", caixa, fonte, fill)

    return _salvar_temp(img, "slide_capa_")


def _slide_preco(valor_mensal, servicos_contratados):
    img = _abrir_slide(12)
    draw = ImageDraw.Draw(img)

    servicos = servicos_contratados or ["Contábil", "Fiscal", "Pessoal", "Societário"]
    servicos_txt = ", ".join(servicos)

    fonte_serv = _font(38)
    fonte_valor = _font(78, bold=True)

    azul = (8, 28, 50)
    dourado = (174, 144, 60)

    # Cobre os textos fixos do slide para reescrever por cima
    draw.rounded_rectangle((250, 250, 1670, 830), radius=45, fill=(255, 255, 255))

    _texto_centralizado(
        draw,
        "Honorários mensais para:",
        (250, 230, 1350, 300),
        _font(54, bold=True, italic=True),
        dourado
    )

    _texto_centralizado(
        draw,
        servicos_txt.lower() + ".",
        (350, 310, 1250, 390),
        fonte_serv,
        dourado
    )

    _texto_centralizado(
        draw,
        _formatar_moeda(valor_mensal),
        (250, 405, 1350, 500),
        fonte_valor,
        azul
    )

    _texto_centralizado(
        draw,
        "*Além disso, será cobrado um honorário adicional em dezembro, no valor dos honorários vigentes, destinado à entrega das obrigações federais, estaduais, municipais e trabalhistas.",
        (320, 555, 1280, 645),
        _font(25),
        azul
    )

    _texto_centralizado(
        draw,
        "* Proposta válida por 10 dias",
        (420, 665, 1180, 710),
        _font(27),
        azul
    )

    return _salvar_temp(img, "slide_preco_")


def _desenhar_card(draw, titulo, bullets, x, y, w, h):
    azul = (12, 39, 67)
    dourado = (190, 157, 70)
    branco = (245, 245, 245)

    draw.rounded_rectangle((x, y, x + w, y + h), radius=28, fill=azul, outline=dourado, width=2)

    draw.rounded_rectangle((x + 25, y + 25, x + w - 25, y + 82), radius=28, outline=dourado, width=2)
    _texto_centralizado(draw, titulo, (x + 35, y + 25, x + w - 35, y + 82), _font(30), dourado)

    fonte_bullet = _font(23)
    cursor_y = y + 120

    for bullet in bullets:
        linhas = _quebrar_texto(bullet, fonte_bullet, w - 90, draw)
        if cursor_y + (len(linhas) * 31) > y + h - 25:
            break

        draw.text((x + 35, cursor_y), "•", font=fonte_bullet, fill=branco)
        linha_y = cursor_y
        for linha in linhas:
            draw.text((x + 65, linha_y), linha, font=fonte_bullet, fill=branco)
            linha_y += 31

        cursor_y = linha_y + 18


def _slide_servicos_dinamico(servicos_contratados, pagina=1):
    servicos = servicos_contratados or ["Contábil", "Fiscal", "Pessoal", "Societário"]

    numero_slide = 8 if pagina == 1 else 9
    img = _abrir_slide(numero_slide)
    draw = ImageDraw.Draw(img)

    # cor aproximada do fundo escuro
    cor_cobertura = (4, 22, 38)

    if pagina == 1:
        blocos = {
            "Contábil": (820, 60, 1225, 1010),
            "Fiscal": (1260, 60, 1665, 1010),
        }
    else:
        blocos = {
            "Pessoal": (820, 60, 1225, 1010),
            "Societário": (1260, 60, 1665, 1010),
        }

    for servico, coords in blocos.items():
        if servico not in servicos:
            draw.rectangle(coords, fill=cor_cobertura)

    return _salvar_temp(img, f"slide_servicos_{pagina}_")


def _adicionar_imagem_pdf(pdf, caminho_img):
    pdf.add_page()
    pdf.image(caminho_img, x=0, y=0, w=297, h=167)


def _adicionar_anexo_respostas(pdf, nome_empresa, respostas):
    if not respostas:
        return

    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, "Anexo - Respostas do Cliente", ln=True)

    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"Empresa: {nome_empresa}", ln=True)
    pdf.cell(0, 8, f"Data de geração: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.ln(5)

    for pergunta, resposta in respostas.items():
        pdf.set_font("Arial", "B", 10)
        pdf.multi_cell(0, 6, str(pergunta))
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, str(resposta))
        pdf.ln(2)


def gerar_pdf_proposta_comercial_v2(
    nome_empresa,
    plano,
    valor_mensal,
    servicos_contratados=None,
    respostas_cliente=None,
    output_dir="propostas_geradas"
):
    os.makedirs(output_dir, exist_ok=True)

    servicos_contratados = servicos_contratados or ["Contábil", "Fiscal", "Pessoal", "Societário"]

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)

    arquivos_temp = []

    try:
        # Slide 1 dinâmico
        capa = _slide_capa(nome_empresa)
        arquivos_temp.append(capa)
        _adicionar_imagem_pdf(pdf, capa)

        # Slides fixos 2 a 7
        for n in [2, 3, 4, 5, 6, 7]:
            caminho = os.path.join(ASSETS_DIR, f"{n}.png")
            _adicionar_imagem_pdf(pdf, caminho)

        # Slides 8 e 9 dinâmicos por serviço contratado
        s8 = _slide_servicos_dinamico(servicos_contratados, pagina=1)
        if s8:
            arquivos_temp.append(s8)
            _adicionar_imagem_pdf(pdf, s8)

        s9 = _slide_servicos_dinamico(servicos_contratados, pagina=2)
        if s9:
            arquivos_temp.append(s9)
            _adicionar_imagem_pdf(pdf, s9)

        # Slides fixos 10 e 11
        for n in [10, 11]:
            caminho = os.path.join(ASSETS_DIR, f"{n}.png")
            _adicionar_imagem_pdf(pdf, caminho)

        # Slide 12 preço dinâmico
        preco = _slide_preco(valor_mensal, servicos_contratados)
        arquivos_temp.append(preco)
        _adicionar_imagem_pdf(pdf, preco)

        # Slides fixos finais
        for n in [13, 14, 15]:
            caminho = os.path.join(ASSETS_DIR, f"{n}.png")
            _adicionar_imagem_pdf(pdf, caminho)

        # Anexo de respostas
        _adicionar_anexo_respostas(pdf, nome_empresa, respostas_cliente or {})

        nome_limpo = "".join(c for c in str(nome_empresa or "proposta") if c.isalnum() or c in (" ", "_", "-")).strip()
        nome_limpo = nome_limpo.replace(" ", "_") or "proposta"

        caminho_pdf = os.path.join(output_dir, f"proposta_v2_{nome_limpo}.pdf")
        pdf.output(caminho_pdf)

        return caminho_pdf

    finally:
        for arq in arquivos_temp:
            try:
                if os.path.exists(arq):
                    os.remove(arq)
            except Exception:
                pass
