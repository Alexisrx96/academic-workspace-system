import json
from pathlib import Path

from academic_workspace.academic_results import build_results_report, write_results_report


def test_results_report_turns_nonconformity_into_action_and_preserves_unknown_score(tmp_path: Path):
    registry = tmp_path / "Control Académico" / "Registro de resultados académicos.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({
        "schema": "academic-results.v1",
        "items": [
            {
                "id": "lab-1",
                "course": "ELE1",
                "title": "Laboratorio 1",
                "kind": "laboratorio",
                "status": "no_conformidad",
                "score": None,
                "score_origin": "no_disponible",
                "score_visibility": "unknown",
                "reason": "Medición incompleta",
                "evidence": "Retroalimentación del docente",
                "source_ref": "[[Blackboard/ELE1/Lab 1]]",
            },
            {
                "id": "group-1",
                "course": "SINF",
                "title": "Proyecto grupal",
                "kind": "actividad",
                "status": "resultado_desconocido",
                "score": None,
                "score_origin": "lider_grupo",
                "score_visibility": "group_leader_only",
            },
        ],
    }, ensure_ascii=False), encoding="utf-8")

    report = build_results_report(tmp_path)

    assert "no_conformidad" in report
    assert "Medición incompleta" in report
    assert "Revisar la rúbrica" in report
    assert "No se infiere una nota" in report
    assert "resultado_desconocido" in report


def test_results_registry_is_created_and_report_is_idempotent(tmp_path: Path):
    first = write_results_report(tmp_path)
    first_content = first.read_text(encoding="utf-8")
    second = write_results_report(tmp_path)

    assert first == second
    assert first_content == second.read_text(encoding="utf-8")
    assert (tmp_path / "Control Académico" / "Registro de resultados académicos.json").is_file()
    assert "No hay accionables" in first_content
