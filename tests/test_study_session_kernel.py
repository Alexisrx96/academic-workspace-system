from academic_workspace.companion_kernel import (
    record_study_session,
    start_study_session,
    study_session,
    study_sessions,
    transition_study_session,
)
from academic_workspace.study_sessions import (
    create_attempt,
    create_session,
    transition_session,
)


def test_study_session_lifecycle_is_persisted(tmp_path):
    session = create_session("FIS1", "Cinemática", "Validar", "explicit_validation", (), 25)
    record_study_session(tmp_path, session)
    active = transition_study_session(tmp_path, session.session_id, "active")

    assert active.status == "active"
    assert study_session(tmp_path, session.session_id).status == "active"


def test_resume_is_persisted_after_pause(tmp_path):
    session = start_study_session(tmp_path, "FIS1", "Cinemática", "Validar", "guided", (), 25)
    transition_study_session(tmp_path, session.session_id, "paused")

    resumed = transition_study_session(tmp_path, session.session_id, "active")

    assert resumed.status == "active"
    assert study_session(tmp_path, session.session_id).status == "active"


def test_session_projection_returns_latest_state_once_per_occurrence(tmp_path):
    first = start_study_session(tmp_path, "FIS1", "Cinemática", "Validar", "guided", (), 25)
    second = start_study_session(tmp_path, "FIS1", "Cinemática", "Validar", "guided", (), 25)
    transition_study_session(tmp_path, first.session_id, "paused")

    projected = study_sessions(tmp_path)

    assert [item.session_id for item in projected] == [first.session_id, second.session_id]
    assert [item.status for item in projected] == ["paused", "active"]


def test_session_cannot_complete_without_a_student_attempt(tmp_path):
    session = start_study_session(tmp_path, "FIS1", "Cinemática", "Comprender", "guided", (), 25)

    try:
        transition_study_session(tmp_path, session.session_id, "completed")
    except ValueError as error:
        assert "intento" in str(error)
    else:
        raise AssertionError("la sesión no debía completarse sin intento")

    from academic_workspace.companion_kernel import record_study_attempt

    record_study_attempt(tmp_path, create_attempt(session, "preflight", "Mi explicación", "", "attempted"))
    completed = transition_study_session(tmp_path, session.session_id, "completed")
    assert completed.status == "completed"


def test_stale_session_snapshot_cannot_overwrite_terminal_state(tmp_path):
    session = start_study_session(tmp_path, "FIS1", "Cinemática", "Comprender", "guided", (), 25)
    stale_paused = transition_session(session, "paused")
    from academic_workspace.companion_kernel import record_study_attempt

    record_study_attempt(tmp_path, create_attempt(session, "preflight", "Mi explicación", "", "attempted"))
    completed = transition_study_session(tmp_path, session.session_id, "completed")
    assert completed.status == "completed"

    try:
        record_study_session(tmp_path, stale_paused)
    except ValueError as error:
        assert "obsoleta" in str(error)
    else:
        raise AssertionError("un snapshot obsoleto no debía reabrir la sesión")


def test_projection_prefers_terminal_state_when_equal_revisions_exist(tmp_path):
    from academic_workspace.memory import JsonlMemoryStore

    session = start_study_session(tmp_path, "FIS1", "Cinemática", "Comprender", "guided", (), 25)
    completed = transition_session(session, "completed")
    paused = transition_session(session, "paused")
    store = JsonlMemoryStore(tmp_path / ".blackboard-sync" / "evidence.jsonl")
    store.append_once("completed-event", {**completed.to_dict(), "event_type": "study.session.state"})
    store.append_once("stale-paused-event", {**paused.to_dict(), "event_type": "study.session.state"})

    assert study_session(tmp_path, session.session_id).status == "completed"


def test_sqlite_rejects_concurrent_transitions_from_the_same_revision(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    from academic_workspace.workspace_commands import init_workspace

    init_workspace(tmp_path)
    session = start_study_session(tmp_path, "FIS1", "Cinemática", "Comprender", "guided", (), 25)
    blocked = transition_session(session, "blocked")
    paused = transition_session(session, "paused")

    def persist(candidate):
        try:
            record_study_session(tmp_path, candidate)
            return "stored"
        except ValueError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(persist, (blocked, paused)))

    assert sorted(results) == ["rejected", "stored"]
    assert study_session(tmp_path, session.session_id).revision == 2
