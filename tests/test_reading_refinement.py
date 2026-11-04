from pathlib import Path

from academic_workspace.reading_refinement import build_refined_readings


def test_refinement_creates_reflowed_linked_derivatives_without_changing_blackboard(tmp_path: Path):
    course = tmp_path / "Blackboard" / "LEMA-V01-022026"
    first = course / "Contenido" / "Semana 2" / "Clases" / "Registros--_1" / "ultraDocumentBody--_2.md"
    second = course / "Contenido" / "Semana 2" / "Clases" / "Movimientos--_3" / "ultraDocumentBody--_4.md"
    assignment = course / "Contenido" / "Semana 2" / "Asignaciones" / "Tarea--_5" / "ultraDocumentBody--_6.md"
    first.parent.mkdir(parents=True)
    (course / "index.md").write_text("# Lenguaje de Máquina\n", encoding="utf-8")
    second.parent.mkdir(parents=True)
    assignment.parent.mkdir(parents=True)
    first.write_text("# ultraDocumentBody\n\n¿Qué son los registros? Los registros almacenan datos en la CPU. Características de los registros Los registros permiten mover datos con rapidez.\n\n![[Adjuntos/diagrama.png]]\n\n## Adjuntos - [registros.png](Adjuntos/registros.png) - [tabla.png](Adjuntos/tabla.png)\n", encoding="utf-8")
    (first.parent / "Adjuntos").mkdir()
    (first.parent / "Adjuntos" / "diagrama.png").write_bytes(b"fixture")
    second.write_text("# ultraDocumentBody\n\nMOV permite copiar datos entre registros. Los registros conservan datos para operaciones.\n", encoding="utf-8")
    assignment.write_text("# ultraDocumentBody\n\nEntregue la tarea.\n", encoding="utf-8")
    original = first.read_text(encoding="utf-8")

    result = build_refined_readings(tmp_path)

    root = tmp_path / "Proyectos de Estudio" / "LEMA - Parcial 1" / "Lecturas refinadas"
    assert result.course_count == 1
    assert result.reading_count == 2
    assert (root / "00 - Índice de lecturas refinadas.md").is_file()
    readings = sorted(root.glob("*.md"))
    assert len(readings) == 3
    rendered = next(path for path in readings if path.name.startswith("Registros--")).read_text(encoding="utf-8")
    assert "## Lectura refinada" in rendered
    assert "### ¿Qué son los registros?" in rendered
    assert "### Características de los registros" in rendered
    assert "![[Blackboard/LEMA-V01-022026/Contenido/Semana 2/Clases/Registros--_1/Adjuntos/diagrama.png]]" in rendered
    assert "## Adjuntos\n\n- [[Blackboard/LEMA-V01-022026/Contenido/Semana 2/Clases/Registros--_1/Adjuntos/registros.png|registros.png]]\n- [[Blackboard/LEMA-V01-022026/Contenido/Semana 2/Clases/Registros--_1/Adjuntos/tabla.png|tabla.png]]" in rendered
    assert "## Resumen del material" in rendered
    assert "## Conexiones por estudiar" in rendered
    assert "[[Blackboard/LEMA-V01-022026/" in rendered
    refined_body = rendered.split("## Lectura refinada\n\n", 1)[1].split("\n\n## Resumen del material", 1)[0]
    assert max(len(line) for line in refined_body.splitlines()) <= 120
    assert first.read_text(encoding="utf-8") == original
