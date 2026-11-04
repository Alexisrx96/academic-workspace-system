from pathlib import Path

from academic_workspace.index_links import refresh_indexes


def test_refresh_indexes_adds_deterministic_child_links(tmp_path: Path):
    container = tmp_path / "Blackboard" / "LEMA" / "Contenido" / "Semana"
    child = container / "Clase--c1"
    child.mkdir(parents=True)
    (container / "index.md").write_text("---\nid: week\n---\n\n# Semana\n", encoding="utf-8")
    (child / "index.md").write_text("# Clase\n", encoding="utf-8")

    first = refresh_indexes(tmp_path)
    second = refresh_indexes(tmp_path)

    assert first["changed"] == 1
    assert second["changed"] == 0
    assert "[[Blackboard/LEMA/Contenido/Semana/Clase--c1/index|Clase]]" in (container / "index.md").read_text(encoding="utf-8")
