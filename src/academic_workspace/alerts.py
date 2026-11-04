from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


_STATE_PATH = ".blackboard-sync/alert-state.json"
_FORMAT = 1


@dataclass(frozen=True, slots=True)
class AlertCandidate:
    key: str
    text: str
    severity: str = "medium"


def _digest(candidate: AlertCandidate) -> str:
    payload = f"{candidate.severity}\0{candidate.text}".encode("utf-8")
    return sha256(payload).hexdigest()


def _load(path: Path) -> dict:
    default = {"format": _FORMAT, "alerts": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    if not isinstance(payload, dict) or payload.get("format") != _FORMAT or not isinstance(payload.get("alerts"), dict):
        return default
    return payload


def _write_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if path.read_text(encoding="utf-8") == content:
            return
    except OSError:
        pass
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)


def collect_new_alerts(target: Path, candidates: tuple[AlertCandidate, ...], *, now: datetime | None = None) -> tuple[AlertCandidate, ...]:
    target = Path(target)
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    path = target / _STATE_PATH
    state = _load(path)
    previous = state["alerts"]
    fresh: list[AlertCandidate] = []
    updated: dict[str, dict[str, str]] = {}
    for candidate in sorted(candidates, key=lambda item: item.key):
        digest = _digest(candidate)
        old = previous.get(candidate.key)
        if not isinstance(old, dict) or old.get("digest") != digest:
            fresh.append(candidate)
        updated[candidate.key] = {
            "digest": digest,
            "last_seen_at": now.isoformat(),
            "severity": candidate.severity,
        }
    for key, value in previous.items():
        if key not in updated and isinstance(value, dict) and isinstance(value.get("digest"), str):
            updated[key] = value
    content = json.dumps({"format": _FORMAT, "alerts": updated}, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    _write_if_changed(path, content)
    return tuple(fresh)
