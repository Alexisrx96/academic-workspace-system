from pathlib import Path
import json

from academic_workspace.task_control import audit_task, calculate_weekly_quota


def test_audit_task_checks_deliverable_sources_and_rubric(tmp_path: Path):
    deliverable = tmp_path / "course" / "deliverable.md"
    deliverable.parent.mkdir(parents=True)
    deliverable.write_text("# Entrega\n\n## Explicación\nTexto.\n", encoding="utf-8")
    source = tmp_path / "Blackboard-UTEC" / "course" / "source.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Fuente\n", encoding="utf-8")
    spec = tmp_path / "task.json"
    spec.write_text(json.dumps({
        "schema": "academic-task.v1",
        "id": "task-1",
        "title": "Tarea",
        "course": "COURSE",
        "origin": "self_directed",
        "deliverables": ["course/deliverable.md"],
        "source_refs": ["Blackboard-UTEC/course/source.md"],
        "rubric": [{"id": "explanation", "criterion": "Explica", "weight": 1, "required_sections": ["Explicación"]}],
    }), encoding="utf-8")

    result = audit_task(spec, tmp_path)

    assert result["status"] == "complete"
    assert result["score"] == 1.0


def test_weekly_quota_reports_remaining_capacity():
    result = calculate_weekly_quota({"capacity_minutes": 200, "planned_minutes": 150, "completed_minutes": 90})
    assert result["remaining_planned_minutes"] == 60
    assert result["remaining_capacity_minutes"] == 50
    assert result["status"] == "in_progress"
