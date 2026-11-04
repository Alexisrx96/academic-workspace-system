from datetime import datetime

from academic_workspace.companion_contracts import (
    EvidenceRecord,
    StudyAction,
    StudyContext,
    StudyEvent,
)


def test_companion_contracts_are_versioned_and_json_stable():
    context = StudyContext(
        priorities=({"course": "SINF", "topic": "SIG"},),
        domain=(),
        reviews=(),
        traceability={},
        source_health={"sync_status": "verified"},
    )
    action = StudyAction(action="start_session", course="SINF", topic="SIG", duration_minutes=25, source_refs=("Blackboard/SINF/SIG.md",), reason="application_score_low")
    event = StudyEvent(event_id="e1", event_type="publication.changed", source_ref="Blackboard/SINF/SIG.md", course="SINF", occurred_at="2026-08-18T12:00:00Z")
    evidence = EvidenceRecord(course="SINF", topic="SIG", explanation_score=2, application_score=1, application_evidence="Caso", boundary_or_doubt="Duda", source_refs=("Blackboard/SINF/SIG.md",), recorded_by="student")

    assert context.to_dict()["schema"] == "study-context.v1"
    assert action.to_dict()["schema"] == "study-action.v1"
    assert event.to_dict()["schema"] == "study-event.v1"
    assert evidence.to_dict()["schema"] == "evidence-record.v1"
    assert StudyContext.from_dict(context.to_dict()) == context


def test_companion_action_rejects_implicit_or_invalid_mutation():
    try:
        StudyAction(action="unknown", course="SINF", topic="SIG", duration_minutes=25, source_refs=(), reason="")
    except ValueError:
        pass
    else:
        raise AssertionError("se esperaba validar la acción")
