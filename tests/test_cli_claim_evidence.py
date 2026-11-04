import json

from academic_workspace.companion_contracts import ExternalSourceRecord
from academic_workspace.companion_kernel import record_external_source
import academic_workspace.cli as cli


def test_study_claim_command_persists_claim_evidence(monkeypatch, capsys, tmp_path):
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
    record_external_source(tmp_path, source)

    assert cli.main([
        "study", "claim", "--target", str(tmp_path),
        "--source-id", source.source_id,
        "--claim", "Afirmación del curso",
        "--quote", "Exact",
        "--verdict", "externally_confirmed",
    ]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema"] == "claim-evidence.v1"
    assert payload["source_url"] == source.url
    assert len((tmp_path / ".blackboard-sync/evidence.jsonl").read_text(encoding="utf-8").splitlines()) == 2
