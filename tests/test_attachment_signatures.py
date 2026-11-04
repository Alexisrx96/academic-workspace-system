from pathlib import Path

from academic_workspace.attachment_signatures import detect_extension


def test_detect_common_attachment_signatures():
    assert detect_extension(b"\x89PNG\r\n\x1a\n") == ".png"
    assert detect_extension(b"\xff\xd8\xff\xe0") == ".jpg"
    assert detect_extension(b"%PDF-1.7") == ".pdf"
    assert detect_extension(b"unknown") is None
