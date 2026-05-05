import os
from datetime import datetime
from jinja2 import Template
from weasyprint import HTML


def formatar_moeda_pdf(valor):
    try:
        valor = float(valor or 0)
    except Exception:
        valor = 0
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


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
    servicos_contratados = servicos_contratados or []

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

            body {
                margin: 0;
                font-family: Arial, sans-serif;
                color: #ffffff;
            }

            .slide {
                width: 297mm;
                height: 210mm;
                page-break-after: always;
                position: relative;
                box-sizing: border-box;
                padding: 35mm;
                background: linear-gradient(135deg, #061421, #142b42);
            }

            .slide-light {
                background: #ffffff;
                color: #0b1f35;
            }

            .logo {
                font-size: 20px;
                letter-spacing: 4px;
                font-weight: bold;
                margin-bottom: 30mm;
            }

            .title {
                font-size: 58px;
                font-weight: 300;
                margin-bottom: 12mm;
            }

            .subtitle {
                font-size: 22px;
                letter-spacing: 8px;
                color: #b69a4a;
            }

            .empresa-box {
                margin-top: 35mm;
                background: #17395a;
                border-radius: 18px;
                padding: 12px 40px;
                display: inline-block;
                min-width: 420px;
                text-align: center;
                font-size: 22px;
            }

            .section-title {
                font-size: 46px;
                color: #b69a4a;
                margin-bottom: 20mm;
                font-weight: bold;
            }

            .text {
                font-size: 24px;
                line-height: 1.45;
                max-width: 680px;
            }

            .cards {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 18mm;
            }

            .card {
                border: 2px solid #b69a4a;
                border-radius: 20px;
                padding: 18mm;
                background: rgba(10, 35, 60, 0.95);
                min-height: 105mm;
            }

            .card h2 {
                color: #d8bd67;
                font-size: 30px;
                margin-top: 0;
                margin-bottom: 12mm;
            }

            .card li {
                font-size: 19px;
                line-height: 1.35;
                margin-bottom: 8px;
            }

            .preco-box {
                background: #ffffff;
                color: #0b1f35;
                border-radius: 28px;
                padding: 28mm;
                text-align: center;
                margin-top: 20mm;
            }

            .preco-box h1 {
                color: #b69a4a;
                font-size: 48px;
                margin: 0 0 8mm 0;
            }

            .servicos-texto {
                color: #b69a4a;
                font-size: 26px;
                margin-bottom: 12mm;
            }

            .valor {
                font-size: 64px;
                font-weight: bold;
                margin-bottom: 10mm;
            }

            .nota {
                font-size: 18px;
                line-height: 1.4;
            }

            .anexo {
                padding: 20mm;
                color: #0b1f35;
                background: #ffffff;
            }

            .anexo h1 {
                font-size: 32px;
                color: #0b1f35;
            }

            .pergunta {
                font-weight: bold;
                margin-top: 10px;
                font-size: 13px;
            }

            .resposta {
                font-size: 13px;
                margin-bottom: 6px;
            }
        </style>
    </head>

    <body>

        <section class="slide">
            <div class="logo">ESCRITA CONTABILIDADE</div>
            <div class="title">Proposta Comercial</div>
            <div class="subtitle">PRESTAÇÃO DE SERVIÇOS CONTÁBEIS</div>
            <div class="empresa-box">{{ nome_empresa }}</div>
        </section>

        <section class="slide">
            <div class="section-title">Sobre a Escrita</div>
            <div class="text">
                Com mais de 40 anos de atuação contábil, a Escrita construiu sua trajetória com foco em segurança técnica,
                planejamento tributário e atuação estratégica em Santa Catarina.
                <br><br>
                Nossa experiência regional, aliada à atualização constante sobre legislação e benefícios fiscais,
                permite oferecer uma visão prática e aplicável à realidade das empresas atendidas.
            </div>
        </section>

        <section class="slide">
            <div class="section-title">Serviços contratados</div>
            <div class="cards">
                {% for servico in servicos %}
                <div class="card">
                    <h2>Área {{ servico.nome }}</h2>
                    <ul>
                        {% for item in servico.itens %}
                        <li>{{ item }}</li>
                        {% endfor %}
                    </ul>
                </div>
                {% endfor %}
            </div>
        </section>

        <section class="slide">
            <div class="preco-box">
                <h1>Honorários mensais para:</h1>
                <div class="servicos-texto">{{ servicos_texto }}</div>
                <div class="valor">{{ valor_formatado }}</div>
                <div class="nota">
                    Plano selecionado: <strong>{{ plano }}</strong><br><br>
                    Além disso, será cobrado um honorário adicional em dezembro, no valor dos honorários vigentes,
                    destinado à entrega das obrigações federais, estaduais, municipais e trabalhistas.
                    <br><br>
                    Proposta válida por 10 dias.
                </div>
            </div>
        </section>

        <section class="slide">
            <div class="section-title">Extras não inclusos</div>
            <div class="cards">
                <div class="card"><h2>Alterações societárias</h2><p>Alteração de contrato social, endereço, quadro societário e atividade.</p></div>
                <div class="card"><h2>Certidões especiais</h2><p>Certidões negativas que não estejam disponíveis para emissão via internet.</p></div>
                <div class="card"><h2>Assessoria tributária</h2><p>Implantação de novos projetos, filiais ou benefícios fiscais específicos.</p></div>
                <div class="card"><h2>BPO Financeiro</h2><p>Gestão financeira de clientes, quando contratada separadamente.</p></div>
            </div>
        </section>

        <section class="slide slide-light">
            <div class="section-title">Agradecemos pela procura</div>
            <div class="text">
                Atenciosamente,<br><br>
                <strong>Rodrigo de Simas Machado</strong><br>
                Responsável Técnico — CRC SC-019217/O-0<br><br>
                Escrita Contabilidade
            </div>
        </section>

        <section class="anexo">
            <h1>Anexo — Respostas do Cliente</h1>
            <p><strong>Empresa:</strong> {{ nome_empresa }}</p>
            <p><strong>Data de geração:</strong> {{ data_geracao }}</p>

            {% for pergunta, resposta in respostas.items() %}
                <div class="pergunta">{{ pergunta }}</div>
                <div class="resposta">{{ resposta }}</div>
            {% endfor %}
        </section>

    </body>
    </html>
    """

    textos_servicos = {
        "Contábil": [
            "Elaboração da contabilidade de acordo com as Normas Brasileiras de Contabilidade.",
            "Emissão de balancetes e DRE.",
            "Envio de obrigações acessórias contábeis obrigatórias."
        ],
        "Fiscal": [
            "Escrituração dos registros fiscais obrigatórios eletrônicos.",
            "Elaboração de guias de contribuições e tributos.",
            "Orientação relativa à tributação das operações da empresa.",
            "Envio de obrigações acessórias fiscais mensais."
        ],
        "Pessoal": [
            "Orientação e controle da aplicação das normas da CLT.",
            "Elaboração de férias, rescisões e manutenção dos registros dos empregados.",
            "Envio dos arquivos relacionados ao eSocial.",
            "Elaboração da folha de pagamento e guias dos encargos sociais."
        ],
        "Societário": [
            "Controle e renovação de alvarás.",
            "Emissão de certidões negativas da empresa.",
            "Acompanhamento de alterações cadastrais e societárias."
        ],
    }

    servicos = [
        {"nome": s, "itens": textos_servicos.get(s, [])}
        for s in servicos_contratados
    ]

    template = Template(html_template)

    html_final = template.render(
        nome_empresa=nome_empresa,
        plano=plano,
        valor_formatado=formatar_moeda_pdf(valor_mensal),
        servicos=servicos,
        servicos_texto=", ".join(servicos_contratados).lower(),
        respostas=respostas_cliente,
        data_geracao=datetime.now().strftime("%d/%m/%Y %H:%M")
    )

    nome_limpo = "".join(c for c in str(nome_empresa or "proposta") if c.isalnum() or c in (" ", "_", "-")).strip()
    nome_limpo = nome_limpo.replace(" ", "_") or "proposta"

    caminho_pdf = os.path.join(output_dir, f"proposta_html_{nome_limpo}.pdf")

    HTML(string=html_final, base_url=".").write_pdf(caminho_pdf)

    return caminho_pdf
