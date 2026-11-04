from pathlib import Path

from academic_workspace.resource_registry import rebuild_resource_registry


def test_resource_registry_keeps_provenance_and_explicit_links(tmp_path: Path):
    official = tmp_path / "Blackboard" / "SINF" / "source.md"
    official.parent.mkdir(parents=True)
    official.write_text("# Fuente\nContenido oficial sobre decisiones.\n", encoding="utf-8")
    personal = tmp_path / "SINF" / "apunte.md"
    personal.parent.mkdir(parents=True)
    personal.write_text(
        '---\nnote_kind: study_note\nsource_ref: "[[Blackboard/SINF/source]]"\n---\n\n# Apunte\nMi explicación.\n',
        encoding="utf-8",
    )

    database = rebuild_resource_registry(tmp_path)

    import sqlite3
    with sqlite3.connect(database) as connection:
        resources = connection.execute("SELECT lane, path, content_hash FROM resources ORDER BY path").fetchall()
        relations = connection.execute("SELECT relation_type, from_path, to_path FROM relations").fetchall()

    assert any(row[0] == "official" for row in resources)
    assert any(row[0] == "work" for row in resources)
    assert ("explicit_link", "SINF/apunte.md", "Blackboard/SINF/source.md") in relations
