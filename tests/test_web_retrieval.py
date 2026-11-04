from pathlib import Path

import pytest

from academic_workspace.web_retrieval import fetch_external_source, html_to_text


def test_html_to_text_removes_scripts_and_preserves_title():
    html = "<html><head><title>Ejemplo</title><script>alert(1)</script></head><body><h1>Concepto</h1><p>Texto útil.</p></body></html>"

    title, text = html_to_text(html)

    assert title == "Ejemplo"
    assert "Texto útil." in text
    assert "alert" not in text


def test_fetch_external_source_creates_provenance_record():
    payload = b"<html><head><title>Fuente</title></head><body><p>Contenido.</p></body></html>"

    source = fetch_external_source(
        "https://example.org/page#fragment",
        purpose="find_examples",
        authorized=True,
        retrieved_at="2026-08-22T12:00:00Z",
        opener=lambda _request, timeout: payload,
    )

    assert source.source_id.startswith("external-source:")
    assert source.url == "https://example.org/page#fragment"
    assert source.title == "Fuente"
    assert len(source.content_hash) == 64
    assert source.authorized is True


def test_fetch_external_source_rejects_unauthorized_lookup():
    with pytest.raises(PermissionError):
        fetch_external_source(
            "https://example.org/page",
            purpose="cross_check",
            authorized=False,
            opener=lambda _request, timeout: b"ignored",
        )
