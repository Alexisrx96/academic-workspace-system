from pathlib import Path
import json

from academic_workspace.execution_summary import build_execution_summary, write_execution_summary


def test_write_execution_summary_persists_versioned_json(tmp_path: Path) -> None:
    path = write_execution_summary(tmp_path)

    assert path == tmp_path / ".blackboard-sync/execution-summary.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "execution-summary.v1"


def test_execution_summary_reports_artifacts_and_verifications(tmp_path: Path) -> None:
    state = tmp_path / ".blackboard-sync"
    state.mkdir()
    (state / "generation-report.json").write_text(json.dumps({"status": "safe", "unexpected_paths": []}), encoding="utf-8")
    (state / "manifest.json").write_text(json.dumps({"files": []}), encoding="utf-8")
    (state / "source-map.json").write_text('{"items": []}', encoding="utf-8")
    (state / "sync-health.json").write_text(json.dumps({"sync_status": "verified"}), encoding="utf-8")
    (state / "execution-verification.json").write_text(json.dumps({"status": "verified", "unexpected_paths": []}), encoding="utf-8")
    (tmp_path / "Control Académico").mkdir()
    (tmp_path / "Control Académico/00 - Dashboard académico.md").write_text("# Dashboard", encoding="utf-8")

    summary = build_execution_summary(tmp_path)

    assert summary["schema"] == "execution-summary.v1"
    assert summary["status"] == "completed"
    assert "Control Académico/00 - Dashboard académico.md" in summary["artifacts"]
    assert summary["verifications"]["manifest_present"] is True
    assert summary["verifications"]["source_map_present"] is True
    assert summary["verifications"]["sync_status"] == "verified"
    assert summary["risks"] == []


def test_execution_summary_marks_missing_evidence_as_partial(tmp_path: Path) -> None:
    summary = build_execution_summary(tmp_path)

    assert summary["status"] == "partial"
    assert summary["risks"] == []


def test_execution_summary_surfaces_blockers_and_missing_evidence(tmp_path: Path) -> None:
    state = tmp_path / ".blackboard-sync"
    state.mkdir()
    (state / "generation-report.json").write_text(json.dumps({
        "status": "blocked",
        "unexpected_paths": ["secret.txt"],
    }), encoding="utf-8")

    summary = build_execution_summary(tmp_path)

    assert summary["status"] == "blocked"
    assert "secret.txt" in summary["risks"]
    assert "manifest_present" in summary["missing_evidence"]
    assert "source_map_present" in summary["missing_evidence"]
