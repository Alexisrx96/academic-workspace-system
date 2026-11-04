from datetime import datetime, timezone
from pathlib import Path

from academic_workspace.study_routines import cancel_pomodoro, start_focus, start_pomodoro, status


def test_pomodoro_is_explicit_and_cancelable(tmp_path: Path):
    now = datetime(2026, 8, 19, 12, tzinfo=timezone.utc)
    started = start_pomodoro(tmp_path, course="SINF", topic="SIG", now=now, minutes=25)
    current = status(tmp_path, now=now.replace(minute=10))

    assert started["status"] == "active"
    assert current["remaining_seconds"] == 15 * 60
    cancelled = cancel_pomodoro(tmp_path, now=now.replace(minute=10))
    assert cancelled["status"] == "cancelled"


def test_focus_mode_allows_one_topic_and_prevents_overlap(tmp_path: Path):
    first = start_focus(tmp_path, course="LEMA", topic="Registros", source_refs=("Blackboard/LEMA/registros.md",))

    assert first["status"] == "active"
    try:
        start_focus(tmp_path, course="SINF", topic="SIG", source_refs=())
    except ValueError as error:
        assert "focus" in str(error).lower()
    else:
        raise AssertionError("se esperaba impedir dos focus modes")
