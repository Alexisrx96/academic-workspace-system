import pytest

from academic_workspace.companion_contracts import ExternalSourceRecord
from academic_workspace.source_validation import build_claim_evidence


def test_claim_evidence_links_claim_quote_snapshot_and_url():
    source = ExternalSourceRecord(
        source_id="external-source:x",
        url="https://example.org/page",
        title="Fuente",
        source_type="web",
        publisher="Example",
        retrieved_at="2026-08-22T12:00:00Z",
        content_hash="a" * 64,
        purpose="cross_check",
        authorized=True,
        snapshot_path=".blackboard-sync/external-sources/a.txt",
        evidence=({"quote": "La velocidad cambia.", "text": "La velocidad cambia."},),
    )

    record = build_claim_evidence("La aceleración cambia la velocidad.", source, "La velocidad cambia.", "externally_confirmed")

    assert record["schema"] == "claim-evidence.v1"
    assert record["claim_id"].startswith("claim:")
    assert record["source_url"] == source.url
    assert record["snapshot_path"] == source.snapshot_path
    assert record["quote"] == "La velocidad cambia."


def test_claim_evidence_rejects_quote_not_registered():
    source = ExternalSourceRecord(
        source_id="external-source:x",
        url="https://example.org/page",
        title="Fuente",
        source_type="web",
        publisher="Example",
        retrieved_at="2026-08-22T12:00:00Z",
        content_hash="a" * 64,
        purpose="cross_check",
        authorized=True,
        evidence=({"quote": "Otra cita.", "text": "Otra cita."},),
    )

    with pytest.raises(ValueError):
        build_claim_evidence("Afirmación", source, "Cita inexistente.", "externally_confirmed")
