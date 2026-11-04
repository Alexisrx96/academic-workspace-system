from pathlib import Path

from academic_workspace.canva_import import (
    extract_canva_html,
    import_canva_html,
    is_canva_url,
)
from academic_workspace.search_index import rebuild_search_index, search


HTML = """<!doctype html>
<html><head><title>Gestión de la información | Canva</title>
<meta property="og:title" content="Gestión de la información" />
<meta property="og:description" content="Conceptos y funciones de la información." />
</head><body><header>Canva Presentación Compartir</header>
<main><h1>Gestión de la información</h1><h2>Funciones principales</h2>
<p>La información apoya la toma de decisiones y la coordinación.</p>
<p>La calidad depende de exactitud, oportunidad y relevancia.</p></main>
<footer>Diseñado con Canva</footer></body></html>"""


def test_detects_canva_links() -> None:
    assert is_canva_url("https://www.canva.com/design/ABC123/view")
    assert is_canva_url("https://canva.link/fl183zodjximeij")
    assert not is_canva_url("https://example.com/canva/design/ABC123")


def test_extracts_visible_presentation_text_without_chrome(tmp_path: Path) -> None:
    result = extract_canva_html(HTML)
    assert result.title == "Gestión de la información"
    assert "La información apoya" in result.body
    assert "Diseñado con Canva" not in result.body
    assert "Canva Presentación" not in result.body


def test_import_preserves_original_and_indexes_note(tmp_path: Path) -> None:
    result = import_canva_html(
        HTML,
        tmp_path,
        source_url="https://www.canva.com/design/ABC123/view",
        accessed_at="2026-08-22T12:00:00-06:00",
        related_courses=["SINF"],
        related_topics=["información"],
    )
    assert result.note.is_file()
    assert result.original.is_file()
    text = result.note.read_text(encoding="utf-8")
    assert 'source_provider: "canva"' in text
    assert "Funciones principales" in text
    rebuild_search_index(tmp_path)
    matches = search(tmp_path, "exactitud oportunidad", lane="external", course="SINF")
    assert matches and matches[0].path == result.note.relative_to(tmp_path).as_posix()
