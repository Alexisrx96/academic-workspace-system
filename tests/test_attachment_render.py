from pathlib import Path

from academic_workspace.models import Snapshot
from academic_workspace.render import render_snapshot


class FakeDownloader:
    def fetch(self, source_url: str) -> bytes:
        assert source_url == "/bbcswebdav/pid-guide/xid-guide"
        return b"%PDF-1.4\nplaceholder\n%%EOF\n"


def test_renderer_places_attachment_with_its_content_note(tmp_path: Path):
    snapshot = Snapshot.from_mapping({
        "courses": [{"id": "course-1", "course_id": "ELE1", "name": "Electrónica"}],
        "activities": [{
            "id": "content-1",
            "course_id": "course-1",
            "kind": "content",
            "title": "Lectura",
            "content_path": ["Semana 1--folder-1"],
            "attachments": [{
                "id": "guide-1",
                "name": "Guía.bin",
                "mime_type": "application/octet-stream",
                "size": 25,
                "source_url": "/bbcswebdav/pid-guide/xid-guide",
            }],
        }],
    })

    result = render_snapshot(snapshot, tmp_path, downloader=FakeDownloader())
    folder = tmp_path / "Blackboard" / "ELE1" / "Contenido" / "Semana 1--folder-1"
    attachment = folder / "Adjuntos" / "Guía--guide-1.bin"
    note = folder / "Lectura--content-1.md"

    assert result.changed
    assert attachment.read_bytes() == b"%PDF-1.4\nplaceholder\n%%EOF\n"
    assert "[Guía.bin](Adjuntos/Guía--guide-1.bin)" in note.read_text(encoding="utf-8")
