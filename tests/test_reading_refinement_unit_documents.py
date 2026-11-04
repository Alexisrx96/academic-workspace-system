from pathlib import Path

from academic_workspace.reading_refinement import build_refined_readings


def test_refinement_includes_attached_reading_inside_a_published_unit(tmp_path: Path):
    course = tmp_path / "Blackboard" / "ADCC-V02-022026"
    source = course / "Contenido" / "Unidad 1" / "Semana 2" / "Adjuntos" / "Interdependencia--_8.pdf.md"
    source.parent.mkdir(parents=True)
    (course / "index.md").write_text("# Administración\n", encoding="utf-8")
    source.write_text("# Interdependencia\n\nUna decisión puede afectar operaciones, finanzas y personal en una organización.\n", encoding="utf-8")

    result = build_refined_readings(tmp_path)

    destination = tmp_path / "Proyectos de Estudio" / "ADCC - Parcial 1" / "Lecturas refinadas"
    assert result.reading_count == 1
    assert any(path.name.startswith("Interdependencia--") for path in destination.glob("*.md"))
