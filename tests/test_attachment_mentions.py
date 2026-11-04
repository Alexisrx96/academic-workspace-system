from academic_workspace.render import _rewrite_attachment_mentions


def test_rewrite_attachment_mentions_embeds_images_and_links_documents():
    body = "logo Utec.png bienvenidos.png F 1 Diseño Instruccional LEMA-V.pdf"
    attachments = [
        ("logo Utec--_1.png", {"name": "logo Utec.png"}, False),
        ("bienvenidos--_2.png", {"name": "bienvenidos.png"}, False),
        ("F 1 Diseño Instruccional LEMA-V--_3.pdf", {"name": "F 1 Diseño Instruccional LEMA-V.pdf"}, True),
    ]

    result = _rewrite_attachment_mentions(body, attachments)

    assert "![[Adjuntos/logo Utec--_1.png]]" in result
    assert "![[Adjuntos/bienvenidos--_2.png]]" in result
    assert "[[Adjuntos/F 1 Diseño Instruccional LEMA-V--_3.pdf]]" in result
