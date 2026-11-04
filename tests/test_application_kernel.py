from pathlib import Path

from academic_workspace import AcademicWorkspaceKernel
from academic_workspace.workspace_commands import init_workspace


def test_public_kernel_exposes_config_status_doctor_and_search(tmp_path: Path):
    init_workspace(tmp_path)
    (tmp_path / "Blackboard" / "SINF").mkdir(parents=True)
    (tmp_path / "Blackboard" / "SINF" / "decision.md").write_text(
        "# Decisiones\n\nLa información apoya decisiones gerenciales.\n", encoding="utf-8"
    )

    kernel = AcademicWorkspaceKernel(tmp_path)

    assert kernel.config()["schema"] == "academic-workspace-config.v1"
    assert kernel.validate_config()["valid"] is True
    assert kernel.doctor()["ok"] is True
    assert kernel.status()["schema"] == "workspace-status.v1"
    assert kernel.search("decisiones", limit=3)[0].title == "Decisiones"
    assert kernel.rag_context("decisiones", mode="lexical")["schema"] == "rag-context.v2"


def test_public_kernel_exposes_empty_memory_and_results_report(tmp_path: Path):
    init_workspace(tmp_path)
    kernel = AcademicWorkspaceKernel(tmp_path)

    assert kernel.memory_events() == []
    assert "Reporte de resultados académicos" in kernel.results_report()
    assert kernel.result_actionables() == ()


def test_application_kernel_lists_latest_study_sessions(tmp_path: Path):
    init_workspace(tmp_path)
    kernel = AcademicWorkspaceKernel(tmp_path)
    session = kernel.start_study_session("FIS1", "Cinemática", "Comprender")

    sessions = kernel.study_sessions()

    assert [item.session_id for item in sessions] == [session.session_id]
