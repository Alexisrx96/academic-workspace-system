from pathlib import Path

from academic_workspace.search_index import rebuild_search_index, search


def test_search_indexes_official_and_external_sources_with_provenance(tmp_path: Path):
    official = tmp_path / "Blackboard" / "SINF" / "Contenido" / "SIG.md"
    official.parent.mkdir(parents=True)
    official.write_text("---\nsource_provider: blackboard_ultra\n---\n# SIG\nLos sistemas gerenciales apoyan decisiones.\n", encoding="utf-8")
    external = tmp_path / "Recursos Externos" / "Libro SIG.md"
    external.parent.mkdir(parents=True)
    external.write_text("---\nresource_kind: book\nsource_url: https://example.org\n---\n# Libro\nLos sistemas gerenciales apoyan decisiones con ejemplos.\n", encoding="utf-8")

    rebuild_search_index(tmp_path)
    results = search(tmp_path, "sistemas gerenciales decisiones")

    assert len(results) == 2
    assert results[0].lane == "official"
    assert results[1].lane == "external"
    assert all(result.excerpt for result in results)
    assert all(result.path for result in results)


def test_search_supports_course_filter(tmp_path: Path):
    for course, text in (("SINF", "sistemas gerenciales"), ("ELE1", "diodos rectificación")):
        path = tmp_path / "Blackboard" / course / f"{course}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {course}\n{text}\n", encoding="utf-8")
    rebuild_search_index(tmp_path)

    results = search(tmp_path, "diodos", course="ELE1")

    assert len(results) == 1
    assert results[0].course == "ELE1"
