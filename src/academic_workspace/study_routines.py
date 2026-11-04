from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


_STATE = ".study-companion/routine-state.json"


def _now(value: datetime | None = None) -> datetime:
    return (value or datetime.now(timezone.utc)).astimezone(timezone.utc)


def _path(target: Path) -> Path:
    return Path(target) / _STATE


def _load(target: Path) -> dict[str, Any]:
    try:
        value = json.loads(_path(target).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"format": 1, "pomodoro": None, "focus": None}
    return value if isinstance(value, dict) else {"format": 1, "pomodoro": None, "focus": None}


def _save(target: Path, value: dict[str, Any]) -> None:
    path = _path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def _active(value: dict[str, Any], key: str) -> bool:
    return isinstance(value.get(key), dict) and value[key].get("status") == "active"


def start_pomodoro(target: Path, *, course: str, topic: str, now: datetime | None = None, minutes: int = 25, break_minutes: int = 5) -> dict[str, Any]:
    if not course or not topic or not 1 <= minutes <= 120 or not 0 <= break_minutes <= 60:
        raise ValueError("curso, tema y duración de Pomodoro inválidos")
    now = _now(now)
    state = _load(target)
    if _active(state, "pomodoro"):
        raise ValueError("ya existe un Pomodoro activo")
    session_id = sha256(f"pomodoro\0{course}\0{topic}\0{now.isoformat()}".encode()).hexdigest()[:16]
    session = {
        "id": session_id,
        "status": "active",
        "course": course,
        "topic": topic,
        "started_at": now.isoformat(),
        "ends_at": (now + timedelta(minutes=minutes)).isoformat(),
        "minutes": minutes,
        "break_minutes": break_minutes,
    }
    state["pomodoro"] = session
    _save(target, state)
    return session


def status(target: Path, *, now: datetime | None = None) -> dict[str, Any]:
    now = _now(now)
    state = _load(target)
    session = state.get("pomodoro")
    if not isinstance(session, dict):
        return {"status": "idle"}
    if session.get("status") == "active":
        ends = datetime.fromisoformat(session["ends_at"])
        remaining = max(0, int((ends - now).total_seconds()))
        if remaining == 0:
            session = {**session, "status": "completed", "completed_at": now.isoformat()}
            state["pomodoro"] = session
            _save(target, state)
        else:
            return {**session, "remaining_seconds": remaining}
    return {**session, "remaining_seconds": 0}


def cancel_pomodoro(target: Path, *, now: datetime | None = None) -> dict[str, Any]:
    current = status(target, now=now)
    if current.get("status") != "active":
        return current
    state = _load(target)
    cancelled = {**state["pomodoro"], "status": "cancelled", "cancelled_at": _now(now).isoformat(), "remaining_seconds": current["remaining_seconds"]}
    state["pomodoro"] = cancelled
    _save(target, state)
    return cancelled


def start_focus(target: Path, *, course: str, topic: str, source_refs: tuple[str, ...] = (), now: datetime | None = None) -> dict[str, Any]:
    if not course or not topic:
        raise ValueError("curso y tema son obligatorios")
    state = _load(target)
    if _active(state, "focus"):
        raise ValueError("ya existe un focus mode activo")
    session = {
        "id": sha256(f"focus\0{course}\0{topic}\0{_now(now).isoformat()}".encode()).hexdigest()[:16],
        "status": "active",
        "course": course,
        "topic": topic,
        "source_refs": list(source_refs),
        "started_at": _now(now).isoformat(),
    }
    state["focus"] = session
    _save(target, state)
    return session


def notify_pomodoro(target: Path, *, now: datetime | None = None) -> dict[str, Any] | None:
    current = status(target, now=now)
    state = _load(target)
    session = state.get("pomodoro")
    if not isinstance(session, dict):
        return None
    if current.get("status") == "active" and not session.get("start_notified"):
        session["start_notified"] = True
        state["pomodoro"] = session
        _save(target, state)
        return {"event": "started", "course": session["course"], "topic": session["topic"], "remaining_seconds": current["remaining_seconds"]}
    if current.get("status") == "completed" and not session.get("end_notified"):
        session["end_notified"] = True
        state["pomodoro"] = session
        _save(target, state)
        return {"event": "completed", "course": session["course"], "topic": session["topic"]}
    return None


def pomodoro_notification_text(event: dict[str, Any]) -> str:
    if event["event"] == "started":
        return f"Pomodoro iniciado · {event['course']} · {event['topic']}"
    return f"Pomodoro terminado · {event['course']} · registra evidencia o toma una pausa"


def stop_focus(target: Path, *, now: datetime | None = None) -> dict[str, Any]:
    state = _load(target)
    focus = state.get("focus")
    if not isinstance(focus, dict) or focus.get("status") != "active":
        return {"status": "idle"}
    stopped = {**focus, "status": "stopped", "stopped_at": _now(now).isoformat()}
    state["focus"] = stopped
    _save(target, state)
    return stopped
