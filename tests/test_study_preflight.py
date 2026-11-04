from academic_workspace.study_preflight import build_preflight


def test_preflight_exposes_policy_sources_and_phs(tmp_path):
    result = build_preflight(
        tmp_path,
        {"session_id": "session:x", "course": "FIS1", "topic": "Cinemática", "mode": "explicit_validation", "source_refs": ["Blackboard/FIS1/Cinematica.md"]},
        phs_status={"installed": True, "version": "0.3.1"},
    )

    assert result["schema"] == "study-preflight.v1"
    assert result["session_id"] == "session:x"
    assert result["source_refs"] == ["Blackboard/FIS1/Cinematica.md"]
    assert result["phs"]["installed"] is True
