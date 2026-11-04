from academic_workspace.confirmation import confirm_file_preview, preview_confirmation_reasons


def test_delete_preview_requires_confirmation():
    preview = [{"operation": "delete", "count": 1, "paths": ["Blackboard/SINF/old.md"]}]

    assert preview_confirmation_reasons(preview) == ["eliminación de archivos"]
    assert confirm_file_preview(preview, input_fn=lambda _prompt: "no") is False
    assert confirm_file_preview(preview, input_fn=lambda _prompt: "si") is True


def test_safe_preview_does_not_prompt():
    preview = [{"operation": "create", "count": 1, "paths": ["Blackboard/SINF/new.md"]}]

    assert preview_confirmation_reasons(preview) == []
    assert confirm_file_preview(preview, input_fn=lambda _prompt: (_ for _ in ()).throw(AssertionError("no debe preguntar"))) is True


def test_yes_flag_approves_destructive_preview():
    preview = [{"operation": "delete", "count": 1, "paths": ["Blackboard/SINF/old.md"]}]

    assert confirm_file_preview(preview, approve=True, input_fn=lambda _prompt: (_ for _ in ()).throw(AssertionError("no debe preguntar"))) is True
