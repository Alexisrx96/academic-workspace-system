from pathlib import Path

from academic_workspace.models import Snapshot
from academic_workspace.render import render_snapshot


def test_renderer_removes_only_stale_files_listed_in_previous_manifest(tmp_path: Path):
    old = Snapshot.from_mapping({
        "courses": [{"id": "c1", "course_id": "ELE1", "name": "Curso"}],
        "activities": [{"id": "a1", "course_id": "c1", "kind": "content", "title": "Anterior"}],
    })
    new = Snapshot.from_mapping({
        "courses": [{"id": "c1", "course_id": "ELE1", "name": "Curso"}],
        "activities": [{"id": "a1", "course_id": "c1", "kind": "content", "title": "Actual"}],
    })
    render_snapshot(old, tmp_path)
    stale = tmp_path / "Blackboard" / "ELE1" / "Contenido" / "Anterior--a1.md"
    unrelated = tmp_path / "Blackboard" / "nota-personal.md"
    unrelated.write_text("no tocar", encoding="utf-8")

    render_snapshot(new, tmp_path)

    assert not stale.exists()
    assert (tmp_path / "Blackboard" / "ELE1" / "Contenido" / "Actual--a1.md").is_file()
    assert unrelated.read_text(encoding="utf-8") == "no tocar"
