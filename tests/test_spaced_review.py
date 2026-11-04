from datetime import date

from academic_workspace.spaced_review import schedule_review


def test_review_schedule_prioritizes_mismatch_and_overconfidence():
    result = schedule_review("calculation_mismatch", confidence=3, today=date(2026, 8, 22))

    assert result["next_review"] == "2026-08-25"
    assert result["interval_days"] == 3
    assert result["reason"] == "calculation_mismatch"


def test_verified_confident_result_gets_longer_interval():
    result = schedule_review("verified", confidence=3, today=date(2026, 8, 22))

    assert result["interval_days"] == 14
    assert result["next_review"] == "2026-09-05"
