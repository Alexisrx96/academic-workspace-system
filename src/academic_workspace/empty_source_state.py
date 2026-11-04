from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .models import Activity, Snapshot

_STATE_RELATIVE = ".blackboard-sync/empty-source-state.json"


@dataclass(frozen=True, slots=True)
class EmptyPolicyResult:
    snapshot: Snapshot
    marked: int
    skipped: int
    reactivated: int


def _key(activity: Activity, provider: str, instance: str) -> str:
    return f"{provider}|{instance}|{activity.course_id}|{activity.id}"


def _is_empty_leaf(activity: Activity) -> bool:
    return (
        not activity.is_container
        and not (activity.body or "").strip()
        and not activity.attachments
        and not activity.due_at
        and not activity.url
    )


def _load(target: Path) -> dict[str, dict[str, str]]:
    try:
        payload = json.loads((target / _STATE_RELATIVE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    items = payload.get("items") if isinstance(payload, dict) else None
    return dict(items) if isinstance(items, dict) else {}


def _save(target: Path, items: dict[str, dict[str, str]]) -> None:
    path = target / _STATE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": "empty-source-state.v1", "items": dict(sorted(items.items()))}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def apply_empty_source_policy(
    snapshot: Snapshot,
    target: Path,
    *,
    provider: str,
    instance: str,
    force: bool,
) -> EmptyPolicyResult:
    """Mark empty leaves and omit them; force re-evaluates existing marks."""
    target = Path(target)
    state = _load(target)
    marked = skipped = reactivated = 0
    included: list[Activity] = []
    for activity in snapshot.activities:
        key = _key(activity, provider, instance)
        was_marked = key in state
        if was_marked and not force:
            if _is_empty_leaf(activity):
                skipped += 1
                continue
            state.pop(key, None)
            reactivated += 1
        if _is_empty_leaf(activity):
            if not was_marked:
                state[key] = {
                    "provider": provider,
                    "instance": instance,
                    "course_id": activity.course_id,
                    "activity_id": activity.id,
                    "title": activity.title,
                }
                marked += 1
            else:
                skipped += 1
            continue
        if was_marked:
            state.pop(key, None)
            reactivated += 1
        included.append(activity)
    _save(target, state)
    return EmptyPolicyResult(Snapshot(snapshot.courses, tuple(included)), marked, skipped, reactivated)
