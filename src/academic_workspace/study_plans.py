from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re


_ROOT = ".study-companion/plans"


def _path(target: Path, plan_id: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,63}", plan_id):
        raise ValueError("plan_id debe ser slug seguro")
    return Path(target) / _ROOT / f"{plan_id}.json"


def _save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def _load(target: Path, plan_id: str) -> dict:
    path = _path(target, plan_id)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"plan inexistente o inválido: {plan_id}") from error
    if value.get("format") != 1 or not isinstance(value.get("steps"), list):
        raise ValueError("formato de plan inválido")
    return value


def create_plan(target: Path, plan_id: str, title: str, course: str, steps: list[dict]) -> dict:
    path = _path(target, plan_id)
    if path.exists():
        raise ValueError(f"el plan ya existe: {plan_id}")
    normalized = []
    for index, step in enumerate(steps, start=1):
        topic = str(step.get("topic", "")).strip()
        minutes = int(step.get("minutes", 25))
        if not topic or minutes <= 0:
            raise ValueError("cada paso requiere topic y minutes positivos")
        normalized.append({
            "step_id": f"{index:03d}",
            "order": index,
            "topic": topic,
            "minutes": minutes,
            "source_refs": list(step.get("source_refs", [])),
            "status": "pending",
        })
    plan = {"format": 1, "plan_id": plan_id, "title": title, "course": course, "status": "active", "steps": normalized}
    _save(path, plan)
    return plan


def next_plan_step(target: Path, plan_id: str) -> dict:
    plan = _load(target, plan_id)
    for step in plan["steps"]:
        if step.get("status") == "pending":
            return {**step, "plan_id": plan_id, "course": plan["course"]}
    return {"plan_id": plan_id, "course": plan["course"], "status": "completed"}


def complete_plan_step(target: Path, plan_id: str, step_id: str) -> dict:
    path = _path(target, plan_id)
    plan = _load(target, plan_id)
    found = False
    for step in plan["steps"]:
        if step.get("step_id") == step_id:
            if step.get("status") == "completed":
                return step
            step["status"] = "completed"
            step["completed_at"] = datetime.now(timezone.utc).isoformat()
            found = True
            break
    if not found:
        raise ValueError(f"paso inexistente: {step_id}")
    if all(step.get("status") == "completed" for step in plan["steps"]):
        plan["status"] = "completed"
    _save(path, plan)
    return next_plan_step(target, plan_id)
