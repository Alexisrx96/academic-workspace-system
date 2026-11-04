from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def schedule_review(result: str, confidence: int | None, *, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    if result in {"calculation_mismatch", "unit_mismatch", "formalization_uncertain"}:
        interval = 3
    elif result in {"verified", "externally_confirmed"} and confidence is not None and confidence >= 2:
        interval = 14
    elif result in {"verified", "externally_confirmed"}:
        interval = 5
    else:
        interval = 2
    return {
        "schema": "study-review.v1",
        "next_review": (today + timedelta(days=interval)).isoformat(),
        "interval_days": interval,
        "reason": result,
        "confidence": confidence,
    }
