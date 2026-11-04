from pathlib import Path

from academic_workspace.empty_source_state import apply_empty_source_policy
from academic_workspace.models import Snapshot


def test_empty_source_policy_skips_and_force_rechecks(tmp_path: Path):
    empty = {"id": "empty", "course_id": "c1", "kind": "content", "title": "Vacío"}
    snapshot = Snapshot.from_mapping({"courses": [{"id": "c1", "name": "Curso"}], "activities": [empty]})

    first = apply_empty_source_policy(snapshot, tmp_path, provider="blackboard_ultra", instance="utec", force=False)
    assert first.snapshot.activities == ()
    assert first.marked == 1

    normal = apply_empty_source_policy(snapshot, tmp_path, provider="blackboard_ultra", instance="utec", force=False)
    assert normal.snapshot.activities == ()
    assert normal.skipped == 1

    with_content = Snapshot.from_mapping({
        "courses": [{"id": "c1", "name": "Curso"}],
        "activities": [{**empty, "body": "Contenido nuevo"}],
    })
    forced = apply_empty_source_policy(with_content, tmp_path, provider="blackboard_ultra", instance="utec", force=True)
    assert [item.id for item in forced.snapshot.activities] == ["empty"]
    assert forced.reactivated == 1


def test_due_activity_is_not_marked_empty(tmp_path: Path):
    snapshot = Snapshot.from_mapping({
        "courses": [{"id": "c1", "name": "Curso"}],
        "activities": [{"id": "a1", "course_id": "c1", "kind": "assignment", "title": "Entrega", "due_at": "2026-08-20"}],
    })
    result = apply_empty_source_policy(snapshot, tmp_path, provider="blackboard_ultra", instance="utec", force=False)
    assert [item.id for item in result.snapshot.activities] == ["a1"]
    assert result.marked == 0
