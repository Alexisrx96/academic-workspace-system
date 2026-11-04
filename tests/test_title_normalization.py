from academic_workspace.models import Activity


def test_activity_title_removes_embedded_attachment_markup():
    activity = Activity.from_mapping({
        "id": "_1",
        "course_id": "c1",
        "title": "[[Adjuntos/GENERALIDADES ADMINISTRACIÓN--_2329014_1.pdf]]",
        "kind": "content",
    })
    assert activity.title == "GENERALIDADES ADMINISTRACIÓN.pdf"


def test_activity_title_removes_image_embed_markup():
    activity = Activity.from_mapping({
        "id": "_2",
        "course_id": "c1",
        "title": "![[Adjuntos/Medición-1N2135A--_2233328_1.jpg]]",
        "kind": "content",
    })
    assert activity.title == "Medición-1N2135A.jpg"
