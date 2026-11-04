from pathlib import Path

from academic_workspace.web_retrieval import fetch_external_source


def test_fetch_external_source_persists_content_snapshot_by_hash(tmp_path: Path):
    payload = b"<html><head><title>Fuente</title></head><body><p>Texto persistente.</p></body></html>"

    source = fetch_external_source(
        "https://example.org/page",
        purpose="find_examples",
        authorized=True,
        artifact_root=tmp_path,
        retrieved_at="2026-08-22T12:00:00Z",
        quotes=("Texto persistente.",),
        opener=lambda _request, timeout: payload,
    )

    snapshot = tmp_path / source.snapshot_path
    assert source.snapshot_path.startswith(".blackboard-sync/external-sources/")
    assert snapshot.read_text(encoding="utf-8") == "Fuente\n\nTexto persistente.\n"
