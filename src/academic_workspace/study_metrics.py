from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .companion_kernel import study_sessions
from .memory import memory_store_for_workspace


def build_study_metrics(target: Path) -> dict[str, Any]:
    attempts = [event for event in memory_store_for_workspace(Path(target)).events() if event.get("schema") == "study-attempt.v1"]
    sessions = study_sessions(target)
    results = Counter(str(event.get("result")) for event in attempts)
    errors = Counter(tag for event in attempts for tag in event.get("error_tags", []))
    session_states = Counter(session.status for session in sessions)
    return {
        "schema": "study-metrics.v1",
        "attempts": len(attempts),
        "sessions": len(sessions),
        "results": dict(sorted(results.items())),
        "errors": dict(sorted(errors.items())),
        "session_states": dict(sorted(session_states.items())),
    }
