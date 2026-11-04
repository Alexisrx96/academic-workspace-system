from academic_workspace.models import Snapshot, canonical_json


def test_canonical_snapshot_does_not_persist_ephemeral_attachment_source_urls():
    base = {
        "courses": [{"id": "c1", "name": "Curso"}],
        "activities": [{
            "id": "a1", "course_id": "c1", "title": "Archivo", "kind": "content",
            "attachments": [{"id": "f1", "name": "guia.pdf", "mime_type": "application/pdf", "size": 10}],
        }],
    }
    first = Snapshot.from_mapping({
        **base,
        "activities": [{**base["activities"][0], "attachments": [{**base["activities"][0]["attachments"][0], "source_url": "/bbcswebdav/first"}]}],
    })
    second = Snapshot.from_mapping({
        **base,
        "activities": [{**base["activities"][0], "attachments": [{**base["activities"][0]["attachments"][0], "source_url": "/bbcswebdav/second"}]}],
    })

    assert canonical_json(first) == canonical_json(second)
    assert "bbcswebdav" not in canonical_json(first)
