from pathlib import Path

import pytest

from academic_workspace.phs_formalization import formalize_phs


def test_phs_formalization_requires_approval_before_writing(tmp_path: Path):
    proposal = formalize_phs(
        tmp_path,
        course="FIS1",
        topic="Cinemática básica",
        script_text="result: 20 m/s\n",
        source_ref="Blackboard/FIS1/Cinematica.md",
        approved=False,
    )

    assert proposal["status"] == "awaiting_approval"
    assert not list(tmp_path.rglob("*.phs"))


def test_approved_phs_formalization_writes_course_calculation(tmp_path: Path):
    result = formalize_phs(
        tmp_path,
        course="FIS1",
        topic="Cinemática básica",
        script_text="result: 20 m/s\n",
        source_ref="Blackboard/FIS1/Cinematica.md",
        approved=True,
    )

    script = tmp_path / result["script_path"]
    assert result["status"] == "created"
    assert script.is_file()
    assert "generated_by: academic-workspace" in script.read_text(encoding="utf-8")
    assert script.as_posix().endswith("02 - Cursos/FIS1/Cálculos/validaciones/cinematica-basica.phs")
