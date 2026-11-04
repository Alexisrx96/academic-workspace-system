from __future__ import annotations

from pathlib import Path
from typing import Any

from .companion_kernel import study_policy
from .memory import memory_store_for_workspace
from .phs_tool import check_phs
from .source_config import load_source_configs


def build_ai_study_context(target: Path, session: dict[str, Any]) -> dict[str, Any]:
    policy = study_policy(target).to_dict()
    mode = session.get("mode", policy["mode"])
    actions = ["record_attempt", "record_evidence", "schedule_review", "advance_phase"]
    if mode in {"explicit_validation", "manual_verification"}:
        actions.extend(["show_answer", "run_phs"])
    if policy["external_lookup"] != "disabled":
        actions.append("search_web")
    evidence = [
        event for event in memory_store_for_workspace(Path(target)).events()
        if event.get("schema") == "claim-evidence.v1" and event.get("session_id") == session.get("session_id")
    ]
    attempts = [
        event for event in memory_store_for_workspace(Path(target)).events()
        if event.get("schema") == "study-attempt.v1" and event.get("session_id") == session.get("session_id")
    ]
    reviews = [
        event for event in memory_store_for_workspace(Path(target)).events()
        if event.get("schema") == "study-review.v1" and event.get("session_id") == session.get("session_id")
    ]
    return {
        "schema": "ai-study-context.v1",
        "session": dict(session),
        "policy": policy,
        "source_health": [
            {"provider": source.provider, "root": source.root, "exists": (Path(target) / source.root).is_dir()}
            for source in load_source_configs(target)
        ],
        "phs": check_phs().to_dict(),
        "external_evidence": evidence,
        "attempts": attempts,
        "reviews": reviews,
        "available_actions": list(dict.fromkeys(actions)),
    }
