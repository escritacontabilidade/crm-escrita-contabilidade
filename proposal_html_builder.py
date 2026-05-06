import os
from datetime import datetime
from jinja2 import Template
from weasyprint import HTML
from num2words import num2words

ASSETS_DIR = "assets_proposta_v2"


def formatar_moeda_pdf(valor):
    try:
        valor = float(valor or 0)
    except Exception:
        valor = 0
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def limpar_nome_arquivo(nome):
    nome = str(nome or "proposta").strip()
    nome = "".join(c for c in nome if c.isalnum() or c in (" ", "_", "-"))
    return nome.replace(" ", "_") or "proposta"


def gerar_pdf_proposta_html(
    nome_empresa,
    plano,
    valor_mensal,
    servicos_contratados,
    respostas_cliente=None,
    output_dir="propostas_geradas"
):
    os.makedirs(output_dir, exist_ok=True)

    respostas_cliente = respostas_cliente or {}
    servicos_contratados = servicos_contratados or ["Contábil", "Fiscal", "Pessoal", "Societário"]

    valor_formatado = formatar_moeda_pdf(valor_mensal)
    valor_extenso = num2words(
        float(valor_mensal),
        lang='pt_BR',
        to='currency'
    )
    
    valor_extenso = valor_extenso.capitalize()
    servicos_texto = ", ".join(servicos_contratados).lower()

    html_template = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">

<style>
    @page {
        size: 1600px 900px;
        margin: 0;
    }

    * {
        box-sizing: border-box;
    }

    body {
        margin: 0;
        padding: 0;
        font-family: Arial, sans-serif;
    }

    .slide {
        width: 1600px;
        height: 900px;
        position: relative;
        page-break-after: always;
        overflow: hidden;
    }

    .slide-bg {
        position: absolute;
        inset: 0;
        width: 1600px;
        height: 900px;
        object-fit: cover;
        z-index: 1;
    }

    .empresa-slide-1 {
        position: absolute;
        z-index: 3;
    
        left: 470px;
        top: 720px;
    
        width: 660px;
        height: 62px;
    
        display: flex;
        align-items: center;
        justify-content: center;
    
        color: #ffffff;
    
        font-size: 30px;
        font-weight: 600;
        letter-spacing: 0.4px;
    
        text-align: center;
    }

    .preco-cover {
        position: absolute;
        z-index: 2;
        left: 185px;
        top: 165px;
        width: 1230px;
        height: 560px;
        background: #ffffff;
        border-radius: 34px;
    }

    .preco-titulo {
        position: absolute;
        z-index: 3;
        left: 230px;
        top: 230px;
        width: 1140px;
        text-align: center;
        color: #b19745;
        font-size: 64px;
        line-height: 1.05;
        font-weight: 800;
        font-style: italic;
    }

    .preco-servicos {
        position: absolute;
        z-index: 3;
        left: 330px;
        top: 340px;
        width: 940px;
        text-align: center;
        color: #a78b3a;
        font-size: 34px;
        line-height: 1.2;
        font-weight: 400;
    }

    .preco-valor {
        position: absolute;
        z-index: 3;
        left: 260px;
        top: 410px;
        width: 1080px;
        text-align: center;
        color: #06192c;
        font-size: 86px;
        line-height: 1.05;
        font-weight: 900;
    }

    .preco-plano {
        position: absolute;
        z-index: 3;
        left: 320px;
        top: 515px;
        width: 960px;
        text-align: center;
        color: #06192c;
        font-size: 28px;
        line-height: 1.2;
        font-weight: 700;
    }

    .preco-nota {
        position: absolute;
        z-index: 3;
        left: 305px;
        top: 585px;
        width: 990px;
        text-align: center;
        color: #06192c;
        font-size: 24px;
        line-height: 1.25;
        font-weight: 400;
    }

    .preco-validade {
        position: absolute;
        z-index: 3;
        left: 400px;
        top: 695px;
        width: 800px;
        text-align: center;
        color: #06192c;
        font-size: 24px;
        line-height: 1.2;
        font-weight: 400;
    }

    .anexo {
        width: 1600px;
        min-height: 900px;
        padding: 70px 95px;
        page-break-after: always;
        background: #ffffff;
        color: #0b1f35;
        font-family: Arial, sans-serif;
    }

    .anexo h1 {
        font-size: 38px;
        margin: 0 0 30px 0;
        color: #0b1f35;
    }

    .anexo-meta {
        font-size: 20px;
        margin-bottom: 35px;
        line-height: 1.45;
    }

    .qa {
        margin-bottom: 18px;
        page-break-inside: avoid;
    }

    .pergunta {
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .resposta {
        font-size: 18px;
        color: #333333;
    }
</style>
</head>

<body>

    {% for n in range(1, 16) %}
        <section class="slide">
            <img class="slide-bg" src="{{ assets_dir }}/{{ n }}.png">

            {% if n == 1 %}
                <div class="empresa-slide-1">{{ nome_empresa }}</div>
            {% endif %}

            {% if n == 12 %}
                <div class="preco-cover"></div>

                <div class="preco-titulo">
                    Honorários mensais para:
                </div>

                <div class="preco-servicos">
                    {{ servicos_texto }}.
                </div>

                <div class="preco-valor">
                    {{ valor_formatado }}
                </div>

                
                <div class="preco-nota">
                    Além disso, será cobrado um honorário adicional em dezembro, no valor dos honorários vigentes,
                    destinado à entrega das obrigações federais, estaduais, municipais e trabalhistas.
                </div>

                <div class="preco-validade">
                    * Proposta válida por 10 dias
                </div>
            {% endif %}
        </section>
    {% endfor %}

    <section class="anexo">
        <h1>Anexo — Respostas do Cliente</h1>

        <div class="anexo-meta">
            <strong>Empresa:</strong> {{ nome_empresa }}<br>
            <strong>Plano:</strong> {{ plano }}<br>
            <strong>Valor mensal:</strong> {{ valor_formatado }}<br>
            <strong>Serviços contratados:</strong> {{ servicos_texto }}<br>
            <strong>Data de geração:</strong> {{ data_geracao }}
        </div>

        {% for pergunta, resposta in respostas.items() %}
            <div class="qa">
                <div class="pergunta">{{ pergunta }}</div>
                <div class="resposta">{{ resposta }}</div>
            </div>
        {% endfor %}
    </section>

</body>
</html>
"""

    template = Template(html_template)

    html_final = template.render(
        assets_dir=ASSETS_DIR,
        nome_empresa=nome_empresa or "Nome da empresa",
        plano=plano or "",
        valor_formatado=valor_formatado,
        servicos_texto=servicos_texto,
        respostas=respostas_cliente,
        data_geracao=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )

    nome_limpo = limpar_nome_arquivo(nome_empresa)
    caminho_pdf = os.path.join(output_dir, f"proposta_{nome_limpo}.pdf")

    HTML(string=html_final, base_url=".").write_pdf(caminho_pdf)

    return caminho_pdf
