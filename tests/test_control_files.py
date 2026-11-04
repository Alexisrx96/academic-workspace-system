import json
from pathlib import Path

from academic_workspace.models import Snapshot
from academic_workspace.render import render_snapshot


def test_renderer_includes_control_map_in_the_manifest(tmp_path: Path):
    snapshot = Snapshot.from_mapping({"courses": [{"id": "c1", "name": "Curso"}], "activities": []})

    render_snapshot(snapshot, tmp_path, control_files={".blackboard-sync/source-map.json": '{"format": 1}\n'})

    manifest = json.loads((tmp_path / ".blackboard-sync" / "manifest.json").read_text(encoding="utf-8"))
    assert (tmp_path / ".blackboard-sync" / "source-map.json").read_text(encoding="utf-8") == '{"format": 1}\n'
    assert ".blackboard-sync/source-map.json" in {entry["path"] for entry in manifest["files"]}
