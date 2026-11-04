from pathlib import Path
import json

from academic_workspace.generation_report import build_generation_report, capture_generation_baseline, write_generation_report


def test_report_uses_current_run_baseline_not_stale_report(tmp_path: Path) -> None:
    personal = tmp_path / "personal.md"
    personal.write_text("already existed", encoding="utf-8")
    baseline = capture_generation_baseline(tmp_path)
    state = tmp_path / ".blackboard-sync"
    state.mkdir()
    (state / "generation-report.json").write_text('{"files": {}}', encoding="utf-8")

    write_generation_report(tmp_path, previous=baseline)
    report = json.loads((state / "generation-report.json").read_text(encoding="utf-8"))

    assert "personal.md" not in report["created"]
    assert report["status"] == "safe"


def test_report_detects_same_size_content_changes(tmp_path: Path) -> None:
    note = tmp_path / "Blackboard-UTEC" / "curso.md"
    note.parent.mkdir()
    note.write_text("aaaa", encoding="utf-8")
    baseline = build_generation_report(tmp_path)

    note.write_text("bbbb", encoding="utf-8")
    report = build_generation_report(tmp_path, baseline)

    assert report["changed"] == ["Blackboard-UTEC/curso.md"]
    assert report["files"]["Blackboard-UTEC/curso.md"]["size"] == 4
    assert len(report["files"]["Blackboard-UTEC/curso.md"]["sha256"]) == 64


def test_report_keeps_legacy_size_only_reports_compatible(tmp_path: Path) -> None:
    note = tmp_path / "Blackboard-UTEC" / "curso.md"
    note.parent.mkdir()
    note.write_text("aaaa", encoding="utf-8")

    legacy = {"files": {"Blackboard-UTEC/curso.md": "4"}}
    report = build_generation_report(tmp_path, legacy)

    assert report["changed"] == []
    assert report["created"] == []


def test_report_blocks_unexpected_root_writes(tmp_path: Path) -> None:
    unexpected = tmp_path / "secret.txt"
    unexpected.write_text("data", encoding="utf-8")

    report = build_generation_report(tmp_path)

    assert report["status"] == "blocked"
    assert report["unexpected_paths"] == ["secret.txt"]


def test_report_allows_the_configured_default_source_root(tmp_path: Path) -> None:
    note = tmp_path / "Blackboard" / "DEMO" / "decision.md"
    note.parent.mkdir(parents=True)
    note.write_text("# Decisión\n", encoding="utf-8")

    report = build_generation_report(tmp_path)

    assert report["status"] == "safe"
    assert report["unexpected_paths"] == []


def test_report_allows_declared_work_control_and_external_lanes(tmp_path: Path) -> None:
    paths = (
        ".hermes/plans/plan.md",
        ".study-companion/routine-state.json",
        "Adjuntos/GENERALIDADES.md",
        "Recursos Externos/00 - Índice.md",
        ".gitignore",
        ".study-companion.example.json",
        "PHYSURE_LANGUAGE_GUIDE.md",
    )
    for relative in paths:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")

    report = build_generation_report(tmp_path)

    assert report["status"] == "safe"
    assert report["unexpected_paths"] == []


def test_report_blocks_deletion_of_an_unexpected_path(tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("data", encoding="utf-8")
    baseline = build_generation_report(tmp_path)
    secret.unlink()

    report = build_generation_report(tmp_path, baseline)

    assert report["deleted"] == ["secret.txt"]
    assert report["status"] == "blocked"
    assert report["unexpected_paths"] == ["secret.txt"]
