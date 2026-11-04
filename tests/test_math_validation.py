import pytest

from academic_workspace.math_validation import validate_phs_result


def test_phs_validation_accepts_matching_value_and_units():
    result = validate_phs_result(
        "FIS1/validacion.phs",
        student_value="20",
        student_units="m/s",
        runner=lambda *_args, **_kwargs: {"verified": True, "stdout": "result: 20 m/s", "stderr": "", "phs_version": "0.3.1"},
    )

    assert result["schema"] == "phs-validation.v1"
    assert result["status"] == "verified"
    assert result["phs_result"]["value"] == 20.0
    assert result["phs_result"]["units"] == "m/s"


def test_phs_validation_detects_unit_mismatch():
    result = validate_phs_result(
        "FIS1/validacion.phs",
        student_value="20",
        student_units="m/s",
        runner=lambda *_args, **_kwargs: {"verified": True, "stdout": "result: 20 km/h", "stderr": "", "phs_version": None},
    )

    assert result["status"] == "unit_mismatch"


def test_phs_validation_reports_unavailable_engine():
    result = validate_phs_result(
        "FIS1/validacion.phs",
        student_value="20",
        student_units="m/s",
        runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("PHS no está instalado")),
    )

    assert result["status"] == "phs_unavailable"
