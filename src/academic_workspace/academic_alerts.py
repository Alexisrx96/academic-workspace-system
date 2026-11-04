from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import re

from .alerts import AlertCandidate
from .study_control import _health_message, _load_health, _parse_datetime


_LINK_RE = re.compile(r"\]\(\.\./(.+?)\)")


def _dashboard_candidates(target: Path) -> list[AlertCandidate]:
    path = target / "Control Académico" / "00 - Dashboard académico.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        section = text.split("## Atención ahora\n", 1)[1].split("\n## ", 1)[0]
    except IndexError:
        return []
    candidates: list[AlertCandidate] = []
    for line in section.splitlines():
        if not line.startswith("- [ ] "):
            continue
        match = _LINK_RE.search(line)
        key = f"dashboard:{match.group(1)}" if match else f"dashboard:text:{sha256(line.encode('utf-8')).hexdigest()}"
        severity = "high" if re.search(r"\*\*\d{4}-\d{2}-\d{2}", line) else "medium"
        if "dominio débil" in line or "Confirmar" in line:
            severity = "medium"
        candidates.append(AlertCandidate(key=key, text=line[6:].strip(), severity=severity))
    return candidates


def _health_candidates(target: Path, *, now: datetime | None = None, stale_after_hours: int = 48) -> list[AlertCandidate]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    health = _load_health(target / ".blackboard-sync" / "sync-health.json")
    status = health.get("sync_status", "unverified")
    if status == "unavailable":
        return [AlertCandidate(
            key="health:unavailable",
            text="Blackboard no está disponible; se conserva el último estado verificado.",
            severity="high",
        )]
    if status != "verified" or not health.get("last_blackboard_sync"):
        return []
    last_sync = _parse_datetime(str(health["last_blackboard_sync"]))
    if last_sync is not None and now - last_sync >= timedelta(hours=stale_after_hours):
        return [AlertCandidate(
            key="health:stale",
            text=f"Blackboard está desactualizado desde {health['last_blackboard_sync']}.",
            severity="medium",
        )]
    return []


def build_candidates(target: Path, *, now: datetime | None = None, stale_after_hours: int = 48) -> tuple[AlertCandidate, ...]:
    target = Path(target)
    candidates = _dashboard_candidates(target) + _health_candidates(target, now=now, stale_after_hours=stale_after_hours)
    return tuple(sorted(candidates, key=lambda candidate: candidate.key))
