import os
import json
from datetime import datetime

def _sanitizar_pdf_text(texto):
    """Remove caracteres que causam problemas no reportlab."""
    if not texto:
        return ""
    # Remove caracteres problemáticos
    chars_para_remover = ['<', '>', '&', '#', '*', '**', '##', '###']
    for char in chars_para_remover:
        texto = texto.replace(char, '')
    return texto


def save_outputs(insights, markdown):
    import os
    os.makedirs("outputs", exist_ok=True)

    # insights
    with open("outputs/insights.json", "w", encoding="utf-8") as f:
        import json
        json.dump(insights, f, ensure_ascii=False, indent=2)

    # markdown
    with open("outputs/dashboard.md", "w", encoding="utf-8") as f:
        f.write(markdown if markdown else "[!] Nenhum conteudo gerado")

    # PDF
    generate_pdf(insights, markdown)


def generate_pdf(insights, markdown):
    """Gera um PDF com toda a análise dos assistentes e agente."""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    except ImportError:
        print("[!] Biblioteca 'reportlab' nao instalada. Pulando geracao de PDF.")
        return

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    output_path = "outputs/analise_completa.pdf"

    # Configuração do documento
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#1f4788"),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#2e5c8a"),
        spaceAfter=12,
        spaceBefore=12,
        fontName="Helvetica-Bold",
    )

    normal_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceAfter=10,
    )

    # Conteúdo
    story = []

    # Título
    story.append(Paragraph("ANALISE COMPLETA - DASHBOARD IA", title_style))
    story.append(Paragraph(f"<i>Gerado em: {timestamp}</i>", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # Resumo dos insights
    story.append(Paragraph("RESUMO EXECUTIVO", heading_style))
    story.append(Spacer(1, 0.1 * inch))

    for area, conteudo in insights.items():
        if isinstance(conteudo, str) and conteudo.strip():
            # Limita tamanho para evitar PDFs muito grandes
            preview = conteudo[:500] + "..." if len(conteudo) > 500 else conteudo
            area_formatted = area.replace("_", " ").upper()
            story.append(Paragraph(f"<b>{area_formatted}</b>", styles["Heading3"]))
            preview_sanitizado = _sanitizar_pdf_text(preview)
            if preview_sanitizado.strip():
                story.append(Paragraph(preview_sanitizado, normal_style))
            story.append(Spacer(1, 0.1 * inch))

    story.append(PageBreak())

    # Analise consolidada (Markdown convertido)
    story.append(Paragraph("ANALISE CONSOLIDADA DO AGENTE DECISOR", heading_style))
    story.append(Spacer(1, 0.1 * inch))

    if markdown:
        # Remove marcadores markdown e formata para o PDF
        markdown_limpo = markdown.replace("## ", "").replace("# ", "")
        # Limita tamanho
        if len(markdown_limpo) > 2000:
            markdown_limpo = markdown_limpo[:2000] + "\n\n[Analise completa disponivel em 'dashboard.md']"

        for linha in markdown_limpo.split("\n"):
            if linha.strip():
                linha_sanitizada = _sanitizar_pdf_text(linha)
                if linha_sanitizada.strip():
                    story.append(Paragraph(linha_sanitizada, normal_style))
    else:
        story.append(Paragraph("[!] Nenhuma analise consolidada gerada.", normal_style))

    story.append(Spacer(1, 0.2 * inch))

    # Rodapé
    footer_text = f"<i>Relatório gerado automaticamente em {timestamp}</i>"
    story.append(Paragraph(footer_text, styles["Normal"]))

    # Gera o PDF
    try:
        doc.build(story)
        print(f"[OK] PDF gerado com sucesso: {output_path}")
    except Exception as e:
        print(f"[!] Erro ao gerar PDF: {e}")