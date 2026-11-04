from pathlib import Path

from academic_workspace.models import Snapshot
from academic_workspace.render import render_snapshot


def test_container_content_is_rendered_as_its_own_platform_folder(tmp_path: Path):
    snapshot = Snapshot.from_mapping({
        "courses": [{"id": "c1", "course_id": "ELE1", "name": "Electrónica"}],
        "activities": [
            {"id": "folder-1", "course_id": "c1", "kind": "content", "title": "Semana 1", "is_container": True},
            {"id": "doc-1", "course_id": "c1", "kind": "content", "title": "Lectura", "content_path": ["Semana 1--folder-1"]},
        ],
    })

    render_snapshot(snapshot, tmp_path)
    course = tmp_path / "Blackboard" / "ELE1" / "Contenido"

    assert (course / "Semana 1--folder-1" / "index.md").is_file()
    assert (course / "Semana 1--folder-1" / "Lectura--doc-1.md").is_file()
    assert not (course / "Semana 1--folder-1.md").exists()
