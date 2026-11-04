from academic_workspace.models import Snapshot, canonical_json


def test_snapshot_is_canonical_regardless_of_source_order():
    source = {
        "courses": [
            {"id": "c2", "name": "Zeta", "course_id": "ELE"},
            {"id": "c1", "name": "Álgebra", "course_id": "LEMA"},
        ],
        "activities": [
            {"id": "a2", "course_id": "c1", "title": "B", "kind": "assignment"},
            {"id": "a1", "course_id": "c1", "title": "A", "kind": "announcement"},
        ],
    }

    snapshot = Snapshot.from_mapping(source)

    assert [c.id for c in snapshot.courses] == ["c1", "c2"]
    assert [a.id for a in snapshot.activities] == ["a1", "a2"]
    assert canonical_json(snapshot) == canonical_json(Snapshot.from_mapping({
        **source,
        "courses": list(reversed(source["courses"])),
        "activities": list(reversed(source["activities"])),
    }))
