import json
from pathlib import Path

from academic_workspace.study_plans import create_plan, next_plan_step, complete_plan_step


def test_study_plan_is_persistent_and_progresses_deterministically(tmp_path: Path):
    plan = create_plan(tmp_path, "sinf-parcial", "SINF Parcial", "SINF", [
        {"topic": "SIG", "minutes": 25, "source_refs": ["Blackboard/SINF/SIG.md"]},
        {"topic": "Dato e información", "minutes": 25, "source_refs": []},
    ])

    first = next_plan_step(tmp_path, "sinf-parcial")
    complete_plan_step(tmp_path, "sinf-parcial", first["step_id"])
    second = next_plan_step(tmp_path, "sinf-parcial")

    assert plan["status"] == "active"
    assert first["topic"] == "SIG"
    assert second["topic"] == "Dato e información"
    assert json.loads((tmp_path / ".study-companion" / "plans" / "sinf-parcial.json").read_text(encoding="utf-8"))["steps"][0]["status"] == "completed"
