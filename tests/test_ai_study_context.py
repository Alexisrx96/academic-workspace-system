from academic_workspace.ai_study_context import build_ai_study_context


def test_ai_context_contains_session_policy_sources_and_actions(tmp_path):
    result = build_ai_study_context(tmp_path, {
        "session_id": "session:x", "course": "FIS1", "topic": "Cinemática",
        "objective": "Validar", "mode": "explicit_validation", "source_refs": []
    })

    assert result["schema"] == "ai-study-context.v1"
    assert result["session"]["session_id"] == "session:x"
    assert result["policy"]["mode"] == "guided" or result["policy"]["mode"] == "explicit_validation"
    assert "show_answer" in result["available_actions"]
    assert "run_phs" in result["available_actions"]
