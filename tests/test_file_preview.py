from pathlib import Path

from academic_workspace.models import Snapshot
from academic_workspace.source_map import build_source_map
from academic_workspace.file_preview import build_file_preview


def test_file_preview_lists_create_update_and_delete_paths(tmp_path: Path) -> None:
    before = build_source_map(Snapshot.from_mapping({
        "courses": [{"id": "c1", "course_id": "SINF", "name": "Sistemas"}],
        "activities": [{"id": "old", "course_id": "c1", "title": "Antiguo", "body": "x"}],
    }))
    after = build_source_map(Snapshot.from_mapping({
        "courses": [{"id": "c1", "course_id": "SINF", "name": "Sistemas"}],
        "activities": [{"id": "new", "course_id": "c1", "title": "Nuevo", "body": "y"}],
    }))

    preview = build_file_preview(after, before, tmp_path)
    operations = {item["operation"]: set(item["paths"]) for item in preview}

    assert any(path.endswith("Nuevo--new.md") for path in operations["create"])
    assert any(path.endswith("Antiguo--old.md") for path in operations["delete"])


def test_file_preview_marks_existing_missing_file_as_create(tmp_path: Path) -> None:
    current = build_source_map(Snapshot.from_mapping({
        "courses": [{"id": "c1", "course_id": "SINF", "name": "Sistemas"}],
        "activities": [],
    }))

    preview = build_file_preview(current, None, tmp_path)

    assert preview[0]["operation"] == "create"
    assert preview[0]["count"] == len(preview[0]["paths"])
