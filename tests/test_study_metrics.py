from academic_workspace.study_metrics import build_study_metrics


def test_study_metrics_counts_attempt_results_and_errors(tmp_path):
    from academic_workspace.companion_kernel import record_study_attempt
    from academic_workspace.study_sessions import (
        create_attempt,
        create_session,
        transition_session,
    )
    session = transition_session(create_session("FIS1", "Cinemática", "Validar", "explicit_validation", (), 25), "active")
    record_study_attempt(tmp_path, create_attempt(session, "preflight", "x", "feedback", "calculation_mismatch", ("sign_error",)))
    record_study_attempt(tmp_path, create_attempt(session, "preflight", "y", "feedback", "verified", ()))

    result = build_study_metrics(tmp_path)

    assert result["schema"] == "study-metrics.v1"
    assert result["attempts"] == 2
    assert result["results"]["verified"] == 1
    assert result["errors"]["sign_error"] == 1


def test_study_metrics_count_latest_session_state_not_state_events(tmp_path):
    from academic_workspace.companion_kernel import (
        start_study_session,
        transition_study_session,
    )

    session = start_study_session(tmp_path, "FIS1", "Cinemática", "Validar", "guided", (), 25)
    transition_study_session(tmp_path, session.session_id, "paused")
    transition_study_session(tmp_path, session.session_id, "active")

    result = build_study_metrics(tmp_path)

    assert result["sessions"] == 1
    assert result["session_states"] == {"active": 1}
