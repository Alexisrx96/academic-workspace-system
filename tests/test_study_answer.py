from academic_workspace.study_answer import build_study_answer


def test_study_answer_separates_course_and_external_authority():
    result = build_study_answer("Opción B", "Fuente externa respalda el concepto", "La diapositiva simplifica", "La formulación técnica requiere un supuesto", ("course:1", "external:1"))

    assert result["schema"] == "study-answer.v1"
    assert result["course_answer"] == "Opción B"
    assert result["external_support"]
    assert result["source_refs"] == ["course:1", "external:1"]
