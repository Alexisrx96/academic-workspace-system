from pathlib import Path

from docx import Document
from pypdf import PdfWriter

from academic_workspace.document_markdown import extract_to_markdown


def test_extract_to_markdown_reads_docx_text(tmp_path: Path):
    source = tmp_path / "guia.docx"
    document = Document()
    document.add_heading("Guía de laboratorio", level=1)
    document.add_paragraph("Preparar el circuito antes de la clase.")
    document.save(source)

    markdown = extract_to_markdown(source, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    assert "# Guía de laboratorio" in markdown
    assert "Preparar el circuito antes de la clase." in markdown


def test_extract_to_markdown_marks_pdf_without_text_for_ocr(tmp_path: Path):
    source = tmp_path / "vacio.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with source.open("wb") as stream:
        writer.write(stream)

    markdown = extract_to_markdown(source, "application/pdf")

    assert markdown.startswith('---\nsource_file: "vacio.pdf"\nsource_format: "pdf"\nextraction: "ocr-required"\n---\n\n# vacio\n')
    assert "requiere OCR" in markdown
