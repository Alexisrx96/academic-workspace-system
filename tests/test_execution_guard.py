import json
from pathlib import Path

from academic_workspace.execution_guard import create_backup, rollback_backup, verify_execution


def test_backup_and_rollback_restore_changed_and_remove_created(tmp_path: Path) -> None:
    managed = tmp_path / "Blackboard" / "SINF.md"
    managed.parent.mkdir()
    managed.write_text("before", encoding="utf-8")
    backup = create_backup(tmp_path, ["Blackboard/SINF.md", "Blackboard/new.md"])

    managed.write_text("after", encoding="utf-8")
    (tmp_path / "Blackboard/new.md").write_text("new", encoding="utf-8")
    rollback_backup(tmp_path, backup)

    assert managed.read_text(encoding="utf-8") == "before"
    assert not (tmp_path / "Blackboard/new.md").exists()


def test_verify_execution_accepts_authorized_changes(tmp_path: Path) -> None:
    state = tmp_path / ".blackboard-sync"
    state.mkdir()
    report = {
        "schema": "generation-report.v1.1",
        "status": "safe",
        "created": ["Blackboard/SINF/new.md"],
        "changed": [],
        "deleted": [],
        "unexpected_paths": [],
    }
    (state / "generation-report.json").write_text(json.dumps(report), encoding="utf-8")

    result = verify_execution(tmp_path, [{"operation": "create", "paths": ["Blackboard/SINF/new.md"]}])

    assert result["status"] == "verified"
    assert result["unexpected_paths"] == []


def test_verify_execution_blocks_unexpected_changes(tmp_path: Path) -> None:
    state = tmp_path / ".blackboard-sync"
    state.mkdir()
    report = {
        "schema": "generation-report.v1.1",
        "status": "safe",
        "created": ["Blackboard/SINF/new.md", "secret.txt"],
        "changed": [],
        "deleted": [],
        "unexpected_paths": [],
    }
    (state / "generation-report.json").write_text(json.dumps(report), encoding="utf-8")

    result = verify_execution(tmp_path, [{"operation": "create", "paths": ["Blackboard/SINF/new.md"]}])

    assert result["status"] == "blocked"
    assert result["unexpected_paths"] == ["secret.txt"]


def test_verify_execution_ignores_allowed_changes_from_previous_local_refresh(tmp_path: Path) -> None:
    state = tmp_path / ".blackboard-sync"
    state.mkdir()
    report = {
        "schema": "generation-report.v1.1",
        "status": "safe",
        "created": [
            "02 - Cursos/ELE1/unidad1/Problemas/ej.phs",
            "Blackboard-UTEC/ADCC-V02-022026/Recursos Canva/Diapositivas/demo/slide-001.png",
        ],
        "changed": [],
        "deleted": [],
        "unexpected_paths": [],
    }
    (state / "generation-report.json").write_text(json.dumps(report), encoding="utf-8")

    result = verify_execution(tmp_path, [{"operation": "create", "paths": []}])

    assert result["status"] == "verified"
    assert result["unexpected_paths"] == []
