import os
from datetime import datetime
from jinja2 import Template
from weasyprint import HTML


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
    servicos_texto = ", ".join(servicos_contratados).lower()

    html_template = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">

<style>
    @page {
        size: A4 landscape;
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
        width: 297mm;
        height: 210mm;
        position: relative;
        page-break-after: always;
        overflow: hidden;
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }

    .empresa-slide-1 {
        position: absolute;
        left: 91mm;
        top: 162mm;
        width: 115mm;
        height: 14mm;
        text-align: center;
        color: #ffffff;
        font-size: 15pt;
        line-height: 14mm;
        font-weight: 400;
    }

    .preco-servicos {
        position: absolute;
        left: 70mm;
        top: 60mm;
        width: 160mm;
        text-align: center;
        color: #a78b3a;
        font-size: 20pt;
        line-height: 1.2;
        font-weight: 400;
    }

    .preco-valor {
        position: absolute;
        left: 45mm;
        top: 83mm;
        width: 210mm;
        text-align: center;
        color: #07192c;
        font-size: 46pt;
        line-height: 1.1;
        font-weight: 800;
    }

    .preco-plano {
        position: absolute;
        left: 70mm;
        top: 108mm;
        width: 160mm;
        text-align: center;
        color: #07192c;
        font-size: 16pt;
        font-weight: 700;
    }

    .anexo {
        width: 297mm;
        min-height: 210mm;
        padding: 18mm 22mm;
        page-break-after: always;
        background: #ffffff;
        color: #0b1f35;
        font-family: Arial, sans-serif;
    }

    .anexo h1 {
        font-size: 24pt;
        margin: 0 0 8mm 0;
        color: #0b1f35;
    }

    .anexo-meta {
        font-size: 11pt;
        margin-bottom: 8mm;
    }

    .qa {
        margin-bottom: 4mm;
        page-break-inside: avoid;
    }

    .pergunta {
        font-size: 10pt;
        font-weight: 700;
        margin-bottom: 1mm;
    }

    .resposta {
        font-size: 10pt;
        color: #333333;
    }
</style>
</head>

<body>

    {% for n in range(1, 16) %}
        <section class="slide" style="background-image: url('{{ assets_dir }}/{{ n }}.png');">

            {% if n == 1 %}
                <div class="empresa-slide-1">{{ nome_empresa }}</div>
            {% endif %}

            {% if n == 12 %}
                <div class="preco-servicos">{{ servicos_texto }}</div>
                <div class="preco-valor">{{ valor_formatado }}</div>
                <div class="preco-plano">Plano selecionado: {{ plano }}</div>
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
