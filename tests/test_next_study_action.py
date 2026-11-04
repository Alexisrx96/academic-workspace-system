from academic_workspace.next_study_action import next_study_action


def test_next_action_prioritizes_error_correction():
    result = next_study_action("calculation_mismatch", ("sign_error",), confidence=3)

    assert result["action"] == "targeted_practice"
    assert "sign_error" in result["reason"]


def test_next_action_for_verified_low_confidence_retrieves_again():
    result = next_study_action("verified", (), confidence=1)

    assert result["action"] == "retrieval_recheck"
