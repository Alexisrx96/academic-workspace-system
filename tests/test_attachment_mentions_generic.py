from academic_workspace.render import _rewrite_attachment_mentions


def test_rewrite_attachment_mentions_embeds_unmentioned_generic_images():
    body = "Texto de la clase."
    attachments = [
        ("adjunto--_1-embedded-1", {"name": "adjunto", "mime_type": "image/png"}, False),
    ]

    result = _rewrite_attachment_mentions(body, attachments)

    assert "![[Adjuntos/adjunto--_1-embedded-1]]" in result
