from datetime import datetime, timezone
from pathlib import Path

from academic_workspace.alerts import AlertCandidate, collect_new_alerts


def test_alerts_notify_first_seen_only(tmp_path: Path):
    candidate = AlertCandidate(key="due:curso:tarea", text="Tarea vence pronto", severity="high")
    first = collect_new_alerts(tmp_path, (candidate,), now=datetime(2026, 8, 18, tzinfo=timezone.utc))
    second = collect_new_alerts(tmp_path, (candidate,), now=datetime(2026, 8, 18, 1, tzinfo=timezone.utc))

    assert [alert.text for alert in first] == ["Tarea vence pronto"]
    assert second == ()


def test_alerts_notify_again_when_content_changes(tmp_path: Path):
    first = AlertCandidate(key="weak:sinf:sig", text="SINF: practicar SIG (1/3)", severity="medium")
    changed = AlertCandidate(key="weak:sinf:sig", text="SINF: practicar SIG (0/3)", severity="high")

    collect_new_alerts(tmp_path, (first,), now=datetime(2026, 8, 18, tzinfo=timezone.utc))
    alerts = collect_new_alerts(tmp_path, (changed,), now=datetime(2026, 8, 19, tzinfo=timezone.utc))

    assert len(alerts) == 1
    assert alerts[0].text == changed.text
    assert alerts[0].severity == "high"


def test_alerts_are_order_independent_and_state_contains_no_message_history(tmp_path: Path):
    candidates = (
        AlertCandidate(key="b", text="B", severity="low"),
        AlertCandidate(key="a", text="A", severity="low"),
    )
    alerts = collect_new_alerts(tmp_path, tuple(reversed(candidates)), now=datetime(2026, 8, 18, tzinfo=timezone.utc))
    state = (tmp_path / ".blackboard-sync" / "alert-state.json").read_text(encoding="utf-8")

    assert [alert.key for alert in alerts] == ["a", "b"]
    assert '"text"' not in state
    assert '"digest"' in state
