from academic_workspace.models import Snapshot, canonical_json


def test_snapshot_sorts_attachments_for_differential_stability():
    source = {
        "courses": [{"id": "c1", "name": "Curso"}],
        "activities": [{
            "id": "a1", "course_id": "c1", "kind": "content", "title": "Archivo",
            "attachments": [
                {"id": "b", "name": "b.pdf", "source_url": "/bbcswebdav/b"},
                {"id": "a", "name": "a.pdf", "source_url": "/bbcswebdav/a"},
            ],
        }],
    }

    first = Snapshot.from_mapping(source)
    second = Snapshot.from_mapping({
        **source,
        "activities": [{**source["activities"][0], "attachments": list(reversed(source["activities"][0]["attachments"]))}],
    })

    assert [attachment["id"] for attachment in first.activities[0].attachments] == ["a", "b"]
    assert canonical_json(first) == canonical_json(second)
