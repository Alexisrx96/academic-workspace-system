from pathlib import Path

from academic_workspace.models import Snapshot
from academic_workspace.render import render_snapshot


def test_container_index_links_immediate_child_activities(tmp_path: Path):
    snapshot = Snapshot.from_mapping({
        "courses": [{"id": "c1", "course_id": "LEMA", "name": "Lenguaje"}],
        "activities": [
            {"id": "week", "course_id": "c1", "kind": "content", "title": "Semana 1", "is_container": True},
            {"id": "class", "course_id": "c1", "kind": "content", "title": "Clase 1", "content_path": ["Semana 1--week"], "body": "Contenido"},
        ],
    })

    render_snapshot(snapshot, tmp_path)
    index = tmp_path / "Blackboard" / "LEMA" / "Contenido" / "Semana 1--week" / "index.md"

    text = index.read_text(encoding="utf-8")
    assert "## Contenido" in text
    assert "[[Blackboard/LEMA/Contenido/Semana 1--week/Clase 1--class|Clase 1]]" in text
