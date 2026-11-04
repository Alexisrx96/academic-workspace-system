from academic_workspace.models import Activity


def test_ultra_document_body_uses_parent_content_title():
    activity = Activity.from_mapping({
        "id": "_2333163_1",
        "course_id": "_9203_1",
        "title": "ultraDocumentBody",
        "kind": "content",
        "content_path": ["Generales--_2333161_1", "Bienvenida--_2333162_1"],
    })

    assert activity.title == "Bienvenida"
