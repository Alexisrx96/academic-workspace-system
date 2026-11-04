from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .source_config import load_source_configs


_ARTIFACT_PATHS = (
    ".blackboard-sync/generation-report.json",
    ".blackboard-sync/manifest.json",
    ".blackboard-sync/source-map.json",
    ".blackboard-sync/sync-health.json",
    ".blackboard-sync/execution-verification.json",
    "Control Académico/00 - Dashboard académico.md",
    "Control Académico/Estado semanal.md",
    "Control Académico/Reporte de resultados académicos.md",
)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def build_execution_summary(target: Path) -> dict[str, Any]:
    """Build a deterministic, evidence-first summary of the latest local run."""
    target = Path(target)
    state = target / ".blackboard-sync"
    generation = _read_json(state / "generation-report.json")
    health = _read_json(state / "sync-health.json")
    verification = _read_json(state / "execution-verification.json")
    artifacts = [relative for relative in _ARTIFACT_PATHS if (target / relative).is_file()]
    verifications = {
        "generation_report_present": (state / "generation-report.json").is_file(),
        "manifest_present": (state / "manifest.json").is_file(),
        "source_map_present": (state / "source-map.json").is_file(),
        "sync_health_present": (state / "sync-health.json").is_file(),
        "post_write_verification_present": (state / "execution-verification.json").is_file(),
        "sync_status": health.get("sync_status", "unknown"),
        "post_write_status": verification.get("status", "unknown"),
    }
    missing_evidence = [
        name for name, present in verifications.items()
        if name.endswith("_present") and not present
    ]
    risks = [str(path) for path in generation.get("unexpected_paths", []) if isinstance(path, str)]
    risks.extend(str(path) for path in verification.get("unexpected_paths", []) if isinstance(path, str))
    if generation.get("status") == "blocked" and not risks:
        risks.append("generation report blocked without a route detail")
    if verification.get("status") == "blocked" and not risks:
        risks.append("post-write verification blocked without a route detail")
    return {
        "schema": "execution-summary.v1",
        "status": "blocked" if risks else ("partial" if missing_evidence else "completed"),
        "artifacts": artifacts,
        "verifications": verifications,
        "sources": [
            {
                "provider": source.provider,
                "instance": source.instance,
                "root": source.root,
            }
            for source in load_source_configs(target)
        ],
        "missing_evidence": missing_evidence,
        "risks": risks,
    }


def write_execution_summary(target: Path) -> Path:
    target = Path(target)
    path = target / ".blackboard-sync/execution-summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_execution_summary(target)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path
