from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != "academic-task.v1":
        raise ValueError("task spec must use academic-task.v1")
    return value


def _exists_ref(target: Path, ref: str) -> bool:
    value = ref.strip()
    if value.startswith("[["):
        value = value[2:].split("|", 1)[0].rstrip("]]")
    candidates = [target / value, target / f"{value}.md", target / value / "index.md"]
    return any(path.is_file() for path in candidates)


def audit_task(spec_path: Path, target: Path) -> dict[str, Any]:
    spec = _load(spec_path)
    target = Path(target)
    deliverables = []
    for raw in spec.get("deliverables", []):
        path = target / str(raw["path"] if isinstance(raw, dict) else raw)
        deliverables.append({"path": path.relative_to(target).as_posix(), "exists": path.is_file()})
    sources = [{"ref": str(ref), "exists": _exists_ref(target, str(ref))} for ref in spec.get("source_refs", [])]
    text = "\n".join((target / item["path"]).read_text(encoding="utf-8", errors="replace") for item in deliverables if item["exists"])
    criteria = []
    total_weight = sum(float(item.get("weight", 0)) for item in spec.get("rubric", [])) or 1.0
    score = 0.0
    for rubric in spec.get("rubric", []):
        required = [str(section).casefold() for section in rubric.get("required_sections", [])]
        present = [section for section in required if section in text.casefold()]
        met = len(present) == len(required)
        weight = float(rubric.get("weight", 0))
        if met:
            score += weight
        criteria.append({"id": rubric.get("id"), "criterion": rubric.get("criterion", ""), "weight": weight, "status": "met" if met else "missing", "missing_sections": [section for section in required if section not in present]})
    normalized_score = round(score / total_weight, 4)
    complete = all(item["exists"] for item in deliverables) and all(item["exists"] for item in sources) and all(item["status"] == "met" for item in criteria)
    return {"schema": "academic-task-audit.v1", "task_id": spec["id"], "title": spec.get("title", spec["id"]), "course": spec.get("course", ""), "origin": spec.get("origin", "self_directed"), "status": "complete" if complete else "in_progress", "score": normalized_score, "deliverables": deliverables, "sources": sources, "criteria": criteria}


def calculate_weekly_quota(config: dict[str, Any]) -> dict[str, Any]:
    capacity = max(0, int(config.get("capacity_minutes", 0)))
    planned = max(0, int(config.get("planned_minutes", 0)))
    completed = max(0, int(config.get("completed_minutes", 0)))
    remaining_planned = max(0, planned - completed)
    remaining_capacity = max(0, capacity - planned)
    status = "complete" if completed >= planned and planned > 0 else "over_capacity" if planned > capacity else "in_progress"
    return {"schema": "weekly-study-quota.v1", "capacity_minutes": capacity, "planned_minutes": planned, "completed_minutes": completed, "remaining_planned_minutes": remaining_planned, "remaining_capacity_minutes": remaining_capacity, "status": status}
