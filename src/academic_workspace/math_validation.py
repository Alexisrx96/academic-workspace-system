from __future__ import annotations

import re
from typing import Any, Callable

_NUMBER_RE = re.compile(r"(?:result|resultado)\s*[:=]\s*([-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?)\s*([A-Za-zµΩ°/%^0-9]*)", re.IGNORECASE)


def _number(value: str) -> float:
    return float(value.replace(",", "."))


def validate_phs_result(
    script: str,
    *,
    student_value: str,
    student_units: str,
    predicted_value: str | None = None,
    predicted_units: str = "",
    runner: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    base = {
        "schema": "phs-validation.v1",
        "script_path": script,
        "student_result": {"value": student_value, "units": student_units},
        "prediction": {"value": predicted_value, "units": predicted_units, "status": "not_provided"},
        "phs_result": None,
    }
    try:
        execution = runner(script)
    except (OSError, RuntimeError, TimeoutError) as error:
        return {**base, "status": "phs_unavailable", "error": str(error)}
    if not execution.get("verified"):
        return {**base, "status": "script_failed", "error": execution.get("stderr", "PHS execution failed")}
    match = _NUMBER_RE.search(str(execution.get("stdout", "")))
    if not match:
        return {**base, "status": "formalization_uncertain", "error": "PHS no devolvió una línea result/resultado interpretable"}
    phs_value = _number(match.group(1))
    phs_units = match.group(2) or ""
    phs_result = {"value": phs_value, "units": phs_units}
    if student_units and phs_units and student_units != phs_units:
        status = "unit_mismatch"
    else:
        try:
            status = "verified" if abs(_number(student_value) - phs_value) <= 1e-9 else "calculation_mismatch"
        except ValueError:
            status = "formalization_uncertain"
    if predicted_value is not None:
        try:
            prediction_ok = abs(_number(predicted_value) - phs_value) <= 1e-9 and (not predicted_units or not phs_units or predicted_units == phs_units)
            prediction = {"value": _number(predicted_value), "units": predicted_units, "status": "prediction_verified" if prediction_ok else "prediction_mismatch"}
        except ValueError:
            prediction = {"value": predicted_value, "units": predicted_units, "status": "prediction_unreadable"}
    else:
        prediction = {"value": None, "units": "", "status": "not_provided"}
    return {
        **base,
        "status": status,
        "phs_result": phs_result,
        "prediction": prediction,
        "phs_version": execution.get("phs_version"),
        "assumptions": [],
        "limitations": [],
    }
