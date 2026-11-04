import json

import academic_workspace.cli as cli


def test_study_policy_command_returns_safe_defaults(capsys, tmp_path):
    assert cli.main(["study", "policy", "--target", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema"] == "study-session-policy.v1"
    assert payload["mode"] == "guided"
    assert payload["external_lookup"] == "ask_first"


def test_study_validate_command_returns_explicit_verdict(capsys, tmp_path):
    assert cli.main([
        "study", "validate", "--target", str(tmp_path),
        "--course-claim", "La velocidad es constante.",
        "--external-claim", "La velocidad puede cambiar.",
        "--relationship", "conflict",
        "--external-evidence",
    ]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["verdict"] == "course_conflict"
    assert payload["course_claim_preserved"] is True
