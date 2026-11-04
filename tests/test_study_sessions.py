import pytest

from academic_workspace.study_sessions import (
    create_session,
    transition_session,
)


def test_study_session_has_versioned_state_and_phases():
    session = create_session(
        course="FIS1",
        topic="Cinemática",
        objective="Validar el procedimiento",
        mode="explicit_validation",
        source_refs=("Blackboard/FIS1/Cinematica.md",),
        planned_minutes=25,
    )

    payload = session.to_dict()

    assert payload["schema"] == "study-session.v1"
    assert payload["status"] == "planned"
    assert payload["current_phase"] == "preflight"
    assert "validation" in payload["phases"]


def test_session_transitions_are_validated():
    session = create_session("FIS1", "Cinemática", "Validar", "explicit_validation", (), 25)
    active = transition_session(session, "active")
    paused = transition_session(active, "paused")
    resumed = transition_session(paused, "active")
    completed = transition_session(resumed, "completed")

    assert completed.status == "completed"
    with pytest.raises(ValueError):
        transition_session(completed, "active")


def test_equivalent_session_requests_create_distinct_occurrences():
    first = create_session("FIS1", "Cinemática", "Validar", "guided", (), 25)
    second = create_session("FIS1", "Cinemática", "Validar", "guided", (), 25)

    assert first.session_id != second.session_id
    assert first.created_at
    assert second.created_at


def test_transition_increments_revision_and_updates_timestamp():
    session = create_session("FIS1", "Cinemática", "Validar", "guided", (), 25)

    active = transition_session(session, "active")
    paused = transition_session(active, "paused")
    resumed = transition_session(paused, "active")

    assert (session.revision, active.revision, paused.revision, resumed.revision) == (0, 1, 2, 3)
    assert resumed.updated_at >= paused.updated_at
