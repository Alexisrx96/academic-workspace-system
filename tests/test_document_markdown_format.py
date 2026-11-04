from pathlib import Path

from docx import Document

from academic_workspace.document_markdown import extract_to_markdown


def test_docx_markdown_has_deterministic_metadata_and_one_document_title(tmp_path: Path):
    source = tmp_path / "guia.docx"
    document = Document()
    document.add_heading("Guía de laboratorio", level=1)
    document.add_paragraph("Preparar el circuito antes de la clase.")
    document.add_heading("Materiales", level=2)
    document.add_paragraph("Diodo y resistencia.")
    document.save(source)

    markdown = extract_to_markdown(source, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    assert markdown.startswith('---\nsource_file: "guia.docx"\nsource_format: "docx"\nextraction: "structured"\n---\n\n# Guía de laboratorio\n')
    assert "## Materiales" in markdown
    assert "Preparar el circuito antes de la clase." in markdown
    assert markdown.count("# Guía de laboratorio") == 1
