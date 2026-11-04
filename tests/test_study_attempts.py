import pytest

from academic_workspace.study_sessions import (
    StudyAttempt,
    advance_phase,
    create_attempt,
    create_session,
    transition_session,
)


def test_session_advances_phase_and_records_attempt():
    session = transition_session(create_session("FIS1", "Cinemática", "Validar", "explicit_validation", (), 25), "active")
    updated = advance_phase(session)
    attempt = create_attempt(updated, "diagnostic", "20 m/s", "Coincide con PHS", "verified", ("unit_ok",))

    assert updated.current_phase == "diagnostic"
    assert isinstance(attempt, StudyAttempt)
    assert attempt.to_dict()["schema"] == "study-attempt.v1"
    assert attempt.result == "verified"


def test_identical_attempt_payloads_are_distinct_learning_events():
    session = transition_session(create_session("FIS1", "Cinemática", "Validar", "guided", (), 25), "active")

    first = create_attempt(session, "preflight", "respuesta", "", "attempted")
    second = create_attempt(session, "preflight", "respuesta", "", "attempted")

    assert first.attempt_id != second.attempt_id
    assert first.occurred_at
    assert second.occurred_at


def test_attempt_requires_active_session_and_current_phase():
    planned = create_session("FIS1", "Cinemática", "Validar", "guided", (), 25)

    with pytest.raises(ValueError, match="activa"):
        create_attempt(planned, "preflight", "respuesta", "", "attempted")

    active = transition_session(planned, "active")
    with pytest.raises(ValueError, match="fase actual"):
        create_attempt(active, "practice", "respuesta", "", "attempted")


def test_phase_advance_requires_active_session():
    planned = create_session("FIS1", "Cinemática", "Validar", "guided", (), 25)

    with pytest.raises(ValueError, match="activa"):
        advance_phase(planned)
