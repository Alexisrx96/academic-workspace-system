import json
from pathlib import Path

from academic_workspace.cli import main
from academic_workspace.workspace_commands import (
    init_workspace,
    validate_workspace,
    workspace_doctor,
    workspace_status,
)


def test_init_is_idempotent_and_creates_neutral_configuration(tmp_path: Path):
    first = init_workspace(tmp_path)
    second = init_workspace(tmp_path)

    assert first["changed"] is True
    assert second["changed"] is False
    assert (tmp_path / ".blackboard-sync" / "workspace-config.json").is_file()
    assert (tmp_path / ".blackboard-sync" / "sources.json").is_file()
    assert (tmp_path / "Blackboard").is_dir()
    assert validate_workspace(tmp_path)["valid"] is True


def test_status_and_doctor_are_structured(tmp_path: Path):
    init_workspace(tmp_path)

    status = workspace_status(tmp_path)
    doctor = workspace_doctor(tmp_path)

    assert status["schema"] == "workspace-status.v1"
    assert status["config_valid"] is True
    assert doctor["schema"] == "workspace-doctor.v1"
    assert doctor["checks"]["target_directory"] is True
    assert doctor["checks"]["config"] is True


def test_cli_config_validate_returns_json(capsys, tmp_path: Path):
    init_workspace(tmp_path)

    assert main(["config", "validate", "--target", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema"] == "workspace-config-validation.v1"
    assert payload["valid"] is True


def test_validate_workspace_reports_present_but_malformed_configuration(tmp_path: Path):
    init_workspace(tmp_path)
    (tmp_path / ".blackboard-sync" / "workspace-config.json").write_text("{bad", encoding="utf-8")
    (tmp_path / ".blackboard-sync" / "sources.json").write_text("{bad", encoding="utf-8")

    result = validate_workspace(tmp_path)

    assert result["valid"] is False
    assert any("workspace-config.json" in error for error in result["errors"])
    assert any("sources.json" in error for error in result["errors"])


def test_validate_workspace_rejects_non_boolean_privacy_values(tmp_path: Path):
    init_workspace(tmp_path)
    config = json.loads((tmp_path / ".blackboard-sync" / "workspace-config.json").read_text(encoding="utf-8"))
    config["privacy"]["allow_external_sources"] = "false"
    (tmp_path / ".blackboard-sync" / "workspace-config.json").write_text(json.dumps(config), encoding="utf-8")

    result = validate_workspace(tmp_path)

    assert result["valid"] is False
    assert any("booleano" in error for error in result["errors"])


def test_validate_workspace_rejects_malformed_privacy_section(tmp_path: Path):
    init_workspace(tmp_path)
    config = json.loads((tmp_path / ".blackboard-sync" / "workspace-config.json").read_text(encoding="utf-8"))
    config["privacy"] = "false"
    (tmp_path / ".blackboard-sync" / "workspace-config.json").write_text(json.dumps(config), encoding="utf-8")

    result = validate_workspace(tmp_path)

    assert result["valid"] is False
    assert any("privacy" in error for error in result["errors"])
