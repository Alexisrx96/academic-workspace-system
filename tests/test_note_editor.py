import pytest
from academic_workspace.note_editor import save_user_note


def test_editor_saves_only_user_owned_course_notes(tmp_path):
    path=save_user_note(tmp_path,'02 - Cursos/SINF/Apunte.md','# Apunte\n\nTexto')
    assert path.read_text(encoding='utf-8') == '# Apunte\n\nTexto'


def test_editor_rejects_official_source(tmp_path):
    with pytest.raises(PermissionError):
        save_user_note(tmp_path,'Blackboard-UTEC/SINF/fuente.md','no')


def test_editor_rejects_path_escape(tmp_path):
    with pytest.raises(PermissionError):
        save_user_note(tmp_path,'02 - Cursos/../Blackboard-UTEC/fuente.md','no')
