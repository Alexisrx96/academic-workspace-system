import pytest
from academic_workspace.phs_incidents import build_phs_incident, prepare_phs_issue


def test_issue_draft_requires_ready_gate():
    report = build_phs_incident("FIS1", "Cinemática", {"status": "script_failed"}, {"reproducible": True})
    with pytest.raises(ValueError):
        prepare_phs_issue(report)


def test_issue_draft_is_structured_when_gate_is_ready():
    checks = {key: True for key in (
        "reproducible", "minimal_case", "input_verified", "formalization_verified", "units_verified",
        "independent_calculation", "similar_examples_checked", "environment_recorded",
        "phs_version_recorded", "alternative_explanations_excluded")}
    report = build_phs_incident("FIS1", "Cinemática", {"status": "script_failed", "script_path": "case.phs"}, checks)
    draft = prepare_phs_issue(report)
    assert draft["schema"] == "phs-issue-draft.v1"
    assert "Minimal Reproduction" in draft["body"]
