from academic_workspace.browser_source import _plain


def test_plain_preserves_embedded_video_urls():
    html = '<p>Clase</p><iframe src="https://onedrive.live.com/embed?resid=abc"></iframe>'

    result = _plain(html)

    assert "Clase" in result
    assert "https://onedrive.live.com/embed?resid=abc" in result
