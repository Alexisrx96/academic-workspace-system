from pathlib import Path

from academic_workspace.document_markdown import extract_to_markdown


def test_extract_to_markdown_keeps_an_actionable_marker_for_unreadable_pdf(tmp_path: Path):
    source = tmp_path / "danado.pdf"
    source.write_bytes(b"no es un pdf")

    markdown = extract_to_markdown(source, "application/pdf")

    assert markdown.startswith('---\nsource_file: "danado.pdf"\nsource_format: "pdf"\nextraction: "failed"\n---\n\n# danado\n')
    assert "No se pudo extraer" in markdown
