from pathlib import Path

from academic_workspace.external_resources import import_external_resource


def test_external_import_preserves_provenance_and_original(tmp_path: Path):
    source = tmp_path / "lectura.md"
    source.write_text("# Sistemas de información\n\nLos sistemas apoyan decisiones.\n", encoding="utf-8")
    metadata = {
        "resource_kind": "article",
        "title": "Sistemas de información",
        "author": "Autor sintético",
        "source_url": "https://example.org/article",
        "license": "CC BY 4.0",
        "accessed_at": "2026-08-18",
        "related_courses": ["SINF"],
        "related_topics": ["decisiones"],
        "curation_status": "reviewed",
    }

    result = import_external_resource(source, tmp_path, metadata)

    assert result.note.is_file()
    assert result.original.is_file()
    text = result.note.read_text(encoding="utf-8")
    assert 'resource_kind: "article"' in text
    assert 'source_url: "https://example.org/article"' in text
    assert "Los sistemas apoyan decisiones" in text
    assert result.original.read_bytes() == source.read_bytes()


def test_external_import_rejects_missing_provenance(tmp_path: Path):
    source = tmp_path / "libro.md"
    source.write_text("# Libro\n", encoding="utf-8")

    try:
        import_external_resource(source, tmp_path, {"title": "Libro"})
    except ValueError as error:
        assert "license" in str(error)
    else:
        raise AssertionError("se esperaba validar metadatos de procedencia")
