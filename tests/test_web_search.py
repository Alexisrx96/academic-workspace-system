from academic_workspace.web_retrieval import search_web


def test_search_web_requires_authorization_and_returns_discovery_hits():
    document = b'''<a class="result__a" href="https://example.org/a">Primer ejemplo</a>'''

    hits = search_web(
        "movimiento uniforme",
        authorized=True,
        opener=lambda _request, timeout: document,
    )

    assert hits == [{"title": "Primer ejemplo", "url": "https://example.org/a"}]
