from academic_workspace.companion_contracts import ExternalSourceRecord
from academic_workspace.companion_kernel import record_claim_evidence
from academic_workspace.source_validation import build_claim_evidence


def test_claim_evidence_is_persisted_once(tmp_path):
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
        evidence=({"quote": "Exact", "text": "Exact"},),
    )
    record = build_claim_evidence("Afirmación", source, "Exact", "externally_confirmed")

    first = record_claim_evidence(tmp_path, record)
    second = record_claim_evidence(tmp_path, record)

    assert first == second
    assert len((tmp_path / ".blackboard-sync/evidence.jsonl").read_text(encoding="utf-8").splitlines()) == 1
