import json

from academic_workspace import cli


def test_study_session_cli_lifecycle(capsys, tmp_path):
    assert cli.main([
        "study", "start", "--target", str(tmp_path),
        "--course", "FIS1", "--topic", "Cinemática",
        "--objective", "Validar procedimiento", "--mode", "explicit_validation",
    ]) == 0
    started = json.loads(capsys.readouterr().out)
    assert started["status"] == "active"

    assert cli.main([
        "study", "attempt", "--target", str(tmp_path),
        "--session-id", started["session_id"], "--phase", "preflight",
        "--response", "Mi procedimiento", "--result", "attempted",
    ]) == 0
    capsys.readouterr()

    assert cli.main(["study", "complete", "--target", str(tmp_path), "--session-id", started["session_id"]]) == 0
    completed = json.loads(capsys.readouterr().out)
    assert completed["status"] == "completed"


def test_study_session_cli_lists_latest_occurrences(capsys, tmp_path):
    for topic in ("Cinemática", "Dinámica"):
        assert cli.main([
            "study", "start", "--target", str(tmp_path),
            "--course", "FIS1", "--topic", topic,
            "--objective", "Comprender",
        ]) == 0
        capsys.readouterr()

    assert cli.main(["study", "list", "--target", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema"] == "study-session-list.v1"
    assert [item["topic"] for item in payload["sessions"]] == ["Cinemática", "Dinámica"]
