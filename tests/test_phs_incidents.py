from pathlib import Path
import json

from academic_workspace.phs_incidents import build_phs_incident, write_phs_incident


def test_incident_classifies_engine_failure_only_after_all_checks(tmp_path: Path):
    report = build_phs_incident(
        course="FIS1",
        topic="Cinemática",
        validation={"status": "script_failed", "script_path": "x.phs", "phs_version": "0.3.1", "error": "unexpected"},
        checks={
            "reproducible": True,
            "minimal_case": True,
            "input_verified": True,
            "formalization_verified": True,
            "units_verified": True,
            "independent_calculation": True,
            "similar_examples_checked": True,
            "environment_recorded": True,
            "phs_version_recorded": True,
            "alternative_explanations_excluded": True,
        },
    )

    assert report["schema"] == "phs-incident.v1"
    assert report["classification"] == "phs_engine"
    assert report["escalation_status"] == "ready_for_phs_issue"


def test_incident_stays_investigation_when_gate_is_incomplete():
    report = build_phs_incident(
        course="FIS1",
        topic="Cinemática",
        validation={"status": "script_failed"},
        checks={"reproducible": True},
    )

    assert report["escalation_status"] == "needs_more_investigation"
    assert report["classification"] != "phs_engine"


def test_write_incident_creates_json_and_markdown(tmp_path: Path):
    script = tmp_path / "02 - Cursos/FIS1/Cálculos/validaciones/case.phs"
    script.parent.mkdir(parents=True)
    script.write_text("result: 20 m/s\n", encoding="utf-8")
    report = build_phs_incident("FIS1", "Cinemática", {"status": "unit_mismatch", "script_path": script.relative_to(tmp_path).as_posix()}, {})

    paths = write_phs_incident(tmp_path, report)

    assert paths["json"].is_file()
    assert paths["markdown"].is_file()
    assert json.loads(paths["json"].read_text(encoding="utf-8"))["schema"] == "phs-incident.v1"
