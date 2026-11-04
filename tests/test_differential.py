from pathlib import Path

from academic_workspace.differential import check_differential
from academic_workspace.models import Snapshot
from academic_workspace.render import render_snapshot
from academic_workspace.source_map import build_source_map


def test_differential_check_skips_downloads_only_when_map_and_files_match(tmp_path: Path):
    snapshot = Snapshot.from_mapping({"courses": [{"id": "c1", "name": "Curso"}], "activities": []})
    source_map = build_source_map(snapshot)
    render_snapshot(snapshot, tmp_path, control_files={".blackboard-sync/source-map.json": source_map.content})

    unchanged = check_differential(snapshot, tmp_path)
    assert unchanged.no_download_needed
    assert unchanged.diff == {"added": 0, "changed": 0, "removed": 0}

    (tmp_path / "Blackboard" / "c1" / "index.md").write_text("alterado", encoding="utf-8")
    damaged = check_differential(snapshot, tmp_path)
    assert not damaged.no_download_needed
    assert not damaged.integrity_ok
