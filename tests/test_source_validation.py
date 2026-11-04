import pytest

from academic_workspace.companion_contracts import ExternalSourceRecord
from academic_workspace.source_validation import classify_validation, stable_source_id, validate_external_source


def test_stable_source_id_uses_url_and_content_hash():
    first = stable_source_id("https://example.org/page", "a" * 64)
    second = stable_source_id("https://example.org/page", "a" * 64)

    assert first == second
    assert first.startswith("external-source:")


def test_external_validation_requires_authorization_and_literal_quote():
    source = ExternalSourceRecord(
        source_id="external-source:x",
        url="https://example.org/page",
        title="Page",
        source_type="university",
        publisher="University",
        retrieved_at="2026-08-22T12:00:00Z",
        content_hash="a" * 64,
        purpose="cross_check",
        authorized=False,
        evidence=({"quote": "Exact quote", "text": "A different text"},),
    )

    with pytest.raises(ValueError):
        validate_external_source(source)


def test_classification_preserves_explicit_conflict():
    result = classify_validation(
        "La velocidad es constante.",
        "La velocidad puede cambiar.",
        relationship="conflict",
        external_evidence=True,
    )

    assert result["verdict"] == "course_conflict"
    assert result["course_claim"] == "La velocidad es constante."


def test_classification_requires_external_evidence():
    result = classify_validation("A", "B", relationship="consistent", external_evidence=False)

    assert result["verdict"] == "insufficient_evidence"
