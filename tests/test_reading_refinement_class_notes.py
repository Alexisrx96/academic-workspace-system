from pathlib import Path

from academic_workspace.reading_refinement import build_refined_readings


def test_refinement_includes_a_class_note_that_is_not_an_ultra_document_body(tmp_path: Path):
    course = tmp_path / "Blackboard" / "ELE1-V01-022026"
    source = course / "Contenido" / "Semana 1" / "Clases" / "Semiconductores--_1" / "Clase 1.1--_2.md"
    source.parent.mkdir(parents=True)
    (course / "index.md").write_text("# Electrónica\n", encoding="utf-8")
    source.write_text("# Semiconductores\n\nUn semiconductor permite controlar el flujo de corriente en un circuito electrónico.\n", encoding="utf-8")

    result = build_refined_readings(tmp_path)

    destination = tmp_path / "Proyectos de Estudio" / "ELE1 - Parcial 1" / "Lecturas refinadas"
    assert result.reading_count == 1
    assert any(path.name.startswith("Semiconductores--") for path in destination.glob("*.md"))
