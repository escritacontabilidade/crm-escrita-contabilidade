from fpdf import FPDF
import os


def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class PDFProposta(FPDF):
    def header(self):
        self.set_fill_color(26, 42, 68)
        self.rect(0, 0, 5, 297, "F")

        if os.path.exists("Logo Escrita.png"):
            self.image("Logo Escrita.png", 10, 10, 40)

        self.set_xy(60, 15)
        self.set_font("Arial", "B", 16)
        self.set_text_color(26, 42, 68)
        self.cell(140, 10, "PROPOSTA COMERCIAL", 0, 1, "R")
        self.ln(15)

    def footer(self):
        self.set_y(-20)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Escrita Contabilidade | Página {self.page_no()}", 0, 0, "C")


def gerar_pdf(dados, mensal, extras_df):
    pdf = PDFProposta()
    pdf.add_page()

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"CLIENTE: {dados['nome'].upper()}", ln=True)

    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Segmento: {dados['segmento']}", ln=True)
    pdf.ln(10)

    pdf.set_fill_color(26, 42, 68)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(130, 10, "  Serviço Recorrente", 1, 0, "L", True)
    pdf.cell(60, 10, "Valor Mensal", 1, 1, "C", True)

    pdf.set_text_color(0, 0, 0)
    pdf.cell(130, 10, "  Honorários Contábeis", 1)
    pdf.cell(60, 10, f"  {formatar_moeda(mensal)}", 1, 1, "R")

    if extras_df is not None and not extras_df.empty:
        pdf.ln(5)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(130, 10, "  Serviços Extras / Avulsos", 1, 0, "L", True)
        pdf.cell(60, 10, "Valor Único", 1, 1, "C", True)

        for _, row in extras_df.iterrows():
            pdf.cell(130, 10, f"  {row['servico']}", 1)
            pdf.cell(60, 10, f"  {formatar_moeda(row['valor'])}", 1, 1, "R")

    return bytes(pdf.output(dest="S"))
