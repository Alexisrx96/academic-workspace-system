from pathlib import Path

from academic_workspace.application.kernel import AcademicWorkspaceKernel
from academic_workspace.phs_tool import check_phs
from academic_workspace.workspace_commands import init_workspace


def test_phs_status_is_explicit_and_non_fatal():
    status = check_phs()
    payload = status.to_dict()

    assert payload["tool"] == "phs"
    assert payload["preferred_for"] == ["mathematics", "physics"]
    assert isinstance(payload["installed"], bool)
    if not payload["installed"]:
        assert payload["suggestion"]


def test_kernel_exposes_phs_status_without_running_a_script(tmp_path: Path):
    init_workspace(tmp_path)
    status = AcademicWorkspaceKernel(tmp_path).phs_status()

    assert status["tool"] == "phs"
    assert status["preferred_for"] == ["mathematics", "physics"]


def test_phs_recommendation_is_optional_for_physics_and_silent_for_other_topics():
    from academic_workspace.phs_tool import phs_recommendation

    physics = phs_recommendation("Resolver un circuito RC y calcular la corriente")
    history = phs_recommendation("Explicar la Revolución Industrial")
    programming = phs_recommendation("Resolver un problema de programación dinámica con algoritmos")

    assert physics["suggested"] is True
    assert physics["optional"] is True
    assert physics["probability"] >= 0.55
    assert "circuito" in physics["matched_terms"]
    assert history["suggested"] is False
    assert history["optional"] is True
    assert programming["suggested"] is False
    assert programming["probability"] < 0.55
    assert "programación dinámica" in programming["excluded_contexts"]
