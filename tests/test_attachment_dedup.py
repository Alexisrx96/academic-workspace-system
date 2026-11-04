from academic_workspace.render import _rewrite_attachment_mentions


def test_attachment_body_deduplicates_embeds_and_removes_download_urls():
    body = (
        'Texto https://utecvirtual.blackboard.com/bbcswebdav/pid-1/xid-1 '
        '![[Adjuntos/Recortador1.png]] ![[Adjuntos/Recortador1.png]]'
    )
    attachments = [("Recortador1.png", {"name": "Recortador1.png"}, False)]

    result = _rewrite_attachment_mentions(body, attachments)

    assert result.count("![[Adjuntos/Recortador1.png]]") == 1
    assert "bbcswebdav" not in result
