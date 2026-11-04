from academic_workspace.math_validation import validate_phs_result


def test_phs_validation_reports_prediction_calibration():
    result = validate_phs_result(
        "case.phs",
        student_value="20",
        student_units="m/s",
        predicted_value="18",
        predicted_units="m/s",
        runner=lambda _script: {"verified": True, "stdout": "result: 20 m/s", "stderr": ""},
    )

    assert result["prediction"]["status"] == "prediction_mismatch"
