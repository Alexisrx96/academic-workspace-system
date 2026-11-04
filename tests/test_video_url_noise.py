from academic_workspace.browser_source import _plain


def test_plain_removes_html_encoded_link_metadata_from_url():
    html = (
        '<p>https://utecvirtual.blackboard.com/sessions/abc/</p>'
        '&quot;,&quot;linkName&quot;:&quot;![[Adjuntos/imagen.png]]&quot;}'
    )

    result = _plain(html)

    assert 'linkName' not in result
    assert '&quot;' not in result
    assert 'https://utecvirtual.blackboard.com/sessions/abc/' in result
    assert '![[Adjuntos/imagen.png]]' in result
