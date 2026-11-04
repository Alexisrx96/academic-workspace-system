import pytest

from academic_workspace.companion_contracts import ExternalSourceRecord, StudySessionPolicy, ValidationRecord


def test_study_policy_serializes_explicit_validation_and_web_lookup():
    policy = StudySessionPolicy(
        mode="explicit_validation",
        answer_policy="explicit",
        source_policy="course_plus_authorized_external",
        external_lookup="ask_first",
        web_purposes=("find_examples", "cross_check"),
    )

    payload = policy.to_dict()

    assert payload["schema"] == "study-session-policy.v1"
    assert payload["mode"] == "explicit_validation"
    assert payload["web_purposes"] == ["find_examples", "cross_check"]


def test_policy_rejects_unknown_mode():
    with pytest.raises(ValueError):
        StudySessionPolicy(mode="invented")


def test_external_source_and_validation_are_versioned():
    source = ExternalSourceRecord(
        source_id="external-source:abc",
        url="https://example.org/physics",
        title="Physics examples",
        source_type="university",
        publisher="Example University",
        retrieved_at="2026-08-22T12:00:00Z",
        content_hash="a" * 64,
        purpose="find_examples",
        authorized=True,
        evidence=({"quote": "An exact quote", "section": "Examples"},),
    )
    validation = ValidationRecord(
        course_claim="La velocidad es constante.",
        external_claim="La velocidad puede cambiar si hay aceleración.",
        verdict="course_simplification",
        source_refs=("Blackboard/FIS1/Cinematica.md", source.source_id),
        evidence_refs=("An exact quote",),
        assumptions=("El material del curso presenta el caso simplificado.",),
        correction="Distinguir velocidad constante de aceleración constante.",
    )

    assert source.to_dict()["schema"] == "external-source.v1"
    assert validation.to_dict()["schema"] == "validation-record.v1"
