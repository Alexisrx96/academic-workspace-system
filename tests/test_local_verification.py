from pathlib import Path

from academic_workspace.models import Snapshot
from academic_workspace.render import render_snapshot
from academic_workspace.source_map import build_source_map
from academic_workspace.verification import validate_local_output


class _Downloader:
    def fetch(self, _url: str) -> bytes:
        return b"contenido"


def test_local_validation_checks_source_map_and_platform_container_paths(tmp_path: Path):
    snapshot = Snapshot.from_mapping({
        "courses": [{"id": "c1", "course_id": "ELE1", "name": "Curso"}],
        "activities": [
            {"id": "u1", "course_id": "c1", "kind": "content", "title": "Unidad", "is_container": True},
            {"id": "d1", "course_id": "c1", "kind": "content", "title": "Documento", "content_path": ["Unidad--u1"], "attachments": [{"id": "a1", "name": "guia.txt", "mime_type": "text/plain", "source_url": "https://ejemplo.local/a1"}]},
        ],
    })
    source_map = build_source_map(snapshot)
    render_snapshot(snapshot, tmp_path, downloader=_Downloader(), control_files={".blackboard-sync/source-map.json": source_map.content})

    report = validate_local_output(snapshot, tmp_path)

    assert report["source_map_matches_platform"]
    assert report["mapped_notes_missing"] == []
    assert report["container_indexes_missing"] == []
    assert report["document_format_errors"] == []
    assert report["manifest_hash_mismatches"] == []
