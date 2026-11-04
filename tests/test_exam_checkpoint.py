from pathlib import Path

from academic_workspace.exam_checkpoint import build_exam_checkpoint


def test_checkpoint_creates_one_diagnostic_and_guide_per_course_without_writing_blackboard(tmp_path: Path):
    blackboard = tmp_path / "Blackboard"
    for course_id, course_name in (("LEMA-V01-022026", "Lenguaje de Máquina"), ("ELE1-V01-022026", "Electrónica")):
        course = blackboard / course_id
        course.mkdir(parents=True)
        (course / "index.md").write_text(f"# {course_name}\n", encoding="utf-8")

    original = (blackboard / "LEMA-V01-022026" / "index.md").read_text(encoding="utf-8")
    result = build_exam_checkpoint(tmp_path)

    checkpoint = tmp_path / "Control Académico" / "Checkpoint - Parcial 1"
    lema_project = tmp_path / "Proyectos de Estudio" / "LEMA - Parcial 1"
    assert result.course_count == 2
    assert (checkpoint / "00 - Panel del corte.md").is_file()
    assert (lema_project / "Prueba diagnóstica.md").is_file()
    assert (lema_project / "Guía de estudio.md").is_file()
    assert (lema_project / "Proyecto de dominio.md").is_file()
    assert (lema_project / "AGENTS.md").is_file()
    assert "diagnóstico" in (lema_project / "Prueba diagnóstica.md").read_text(encoding="utf-8").lower()
    assert "recuperación" in (lema_project / "Guía de estudio.md").read_text(encoding="utf-8").lower()
    assert (blackboard / "LEMA-V01-022026" / "index.md").read_text(encoding="utf-8") == original


def test_checkpoint_preserves_manual_domain_journal(tmp_path: Path):
    course = tmp_path / "Blackboard" / "SINF-V02-022026"
    course.mkdir(parents=True)
    (course / "index.md").write_text("# Sistemas\n", encoding="utf-8")
    journal = tmp_path / "Proyectos de Estudio" / "SINF - Parcial 1" / "Bitácora de dominio.md"
    journal.parent.mkdir(parents=True)
    original = "# Bitácora propia\n\n| evidencia manual |\n|---|\n| no sobrescribir |\n"
    journal.write_text(original, encoding="utf-8")

    build_exam_checkpoint(tmp_path)

    assert journal.read_text(encoding="utf-8") == original
