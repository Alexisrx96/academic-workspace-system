from pathlib import Path

from academic_workspace.canva_discovery import discover_canva_presentations
from academic_workspace.search_index import rebuild_search_index, search


def test_discovers_imports_and_is_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "Blackboard" / "ADCC-V02-022026" / "Contenido" / "Semana 1.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        '---\nsource_course_id: "_8208_1"\ncourse_code: "ADCC-V02-022026"\n---\n\n'
        "# Semana 1\n\nPresentación: https://www.canva.com/design/DEMO/view.\n",
        encoding="utf-8",
    )
    html = "<html><head><meta property='og:title' content='ADCC Canva'></head><body><main><p>Interacción e interdependencia.</p></main></body></html>"
    calls: list[str] = []

    def fetcher(url: str) -> str:
        calls.append(url)
        return html

    first = discover_canva_presentations(
        tmp_path,
        fetcher=fetcher,
        accessed_at="2026-08-22T12:00:00-06:00",
    )
    second = discover_canva_presentations(tmp_path, fetcher=fetcher)
    assert first.discovered == 1
    assert first.imported[0].note.relative_to(tmp_path).as_posix().startswith("Blackboard/ADCC-V02-022026/Recursos Canva/")
    note_text = first.imported[0].note.read_text(encoding="utf-8")
    assert 'source_lane: "official"' in note_text
    assert (tmp_path / "Blackboard" / "ADCC-V02-022026" / "Recursos Canva" / "index.md").is_file()
    assert second.skipped == 1
    assert not second.imported
    assert len(calls) == 1
    rebuild_search_index(tmp_path)
    assert search(tmp_path, "interacción interdependencia", course="ADCC-V02-022026")


def test_discovers_other_courses_without_a_course_filter(tmp_path: Path) -> None:
    source = tmp_path / "Blackboard" / "OTHER" / "note.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        '---\nsource_course_id: "_999_1"\n---\nhttps://www.canva.com/design/OTHER/view\n',
        encoding="utf-8",
    )
    result = discover_canva_presentations(tmp_path, fetcher=lambda _url: "<p>no</p>")
    assert result.discovered == 1
    assert len(result.imported) == 1
