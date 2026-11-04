from __future__ import annotations

from pathlib import Path
from typing import Any

from .companion_kernel import study_policy
from .phs_tool import check_phs
from .source_config import load_source_configs


def build_preflight(target: Path, session: dict[str, Any], *, phs_status: dict[str, Any] | None = None) -> dict[str, Any]:
    target = Path(target)
    policy = study_policy(target).to_dict()
    sources = [
        {"provider": source.provider, "instance": source.instance, "root": source.root, "exists": (target / source.root).is_dir()}
        for source in load_source_configs(target)
    ]
    return {
        "schema": "study-preflight.v1",
        "session_id": session.get("session_id"),
        "course": session.get("course"),
        "topic": session.get("topic"),
        "objective": session.get("objective"),
        "mode": session.get("mode"),
        "source_refs": list(session.get("source_refs", ())),
        "policy": policy,
        "sources": sources,
        "phs": phs_status or check_phs().to_dict(),
        "warnings": ["source root unavailable" for source in sources if not source["exists"]],
    }
