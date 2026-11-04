from academic_workspace.alerts import AlertCandidate
from academic_workspace.notifications import format_notification


def test_notification_removes_markdown_and_paths():
    payload = format_notification((
        AlertCandidate(
            key="x",
            text="**Confirmar** · [Evaluación parcial](../Blackboard/LEMA/Anuncio.md) — LEMA",
            severity="medium",
        ),
    ))

    assert payload.title == "UTEC · Atención académica"
    assert payload.body == "Confirmar · Evaluación parcial — LEMA"
    assert "Blackboard" not in payload.body
    assert "[" not in payload.body


def test_notification_compacts_multiple_alerts():
    payload = format_notification(tuple(
        AlertCandidate(key=str(i), text=f"**Acción {i}** — Curso", severity="low")
        for i in range(4)
    ))

    assert payload.body == "Acción 0 — Curso\nAcción 1 — Curso\n+2 acciones académicas"
