import pytest

from academic_workspace.web_retrieval import fetch_external_source


def test_fetch_external_source_validates_literal_quotes_against_extracted_text():
    payload = b"<html><head><title>Fuente</title></head><body><p>La aceleracion cambia la velocidad.</p></body></html>"

    source = fetch_external_source(
        "https://example.org/physics",
        purpose="cross_check",
        authorized=True,
        retrieved_at="2026-08-22T12:00:00Z",
        quotes=("La aceleracion cambia la velocidad.",),
        opener=lambda _request, timeout: payload,
    )

    assert source.evidence[0]["quote"] == "La aceleracion cambia la velocidad."
    assert source.evidence[0]["text"]


def test_fetch_external_source_rejects_quote_not_in_page():
    with pytest.raises(ValueError):
        fetch_external_source(
            "https://example.org/physics",
            purpose="cross_check",
            authorized=True,
            quotes=("Texto que no existe.",),
            opener=lambda _request, timeout: b"<p>Contenido diferente.</p>",
        )
