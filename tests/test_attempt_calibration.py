from academic_workspace.study_sessions import (
    create_attempt,
    create_session,
    transition_session,
)


def test_attempt_records_confidence_help_and_calibration():
    session = transition_session(create_session("FIS1", "Cinemática", "Validar", "explicit_validation", (), 25), "active")
    attempt = create_attempt(session, "preflight", "20", "Correcto", "verified", (), confidence=3, help_level=0)
    payload = attempt.to_dict()

    assert payload["confidence"] == 3
    assert payload["help_level"] == 0
    assert payload["calibration"] == "well_calibrated"


def test_incorrect_high_confidence_is_overconfident():
    session = transition_session(create_session("FIS1", "Cinemática", "Validar", "explicit_validation", (), 25), "active")
    attempt = create_attempt(session, "preflight", "25", "Revisar signos", "calculation_mismatch", (), confidence=3, help_level=0)

    assert attempt.to_dict()["calibration"] == "overconfident"
