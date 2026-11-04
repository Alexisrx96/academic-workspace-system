from pathlib import Path

from docx import Document

from academic_workspace.models import Snapshot
from academic_workspace.render import render_snapshot


class FakeDownloader:
    def __init__(self, content: bytes):
        self.content = content

    def fetch(self, source_url: str) -> bytes:
        assert source_url == "/bbcswebdav/pid-doc/xid-doc"
        return self.content


def test_renderer_creates_markdown_sidecar_for_docx_attachment(tmp_path: Path):
    source = tmp_path / "source.docx"
    document = Document()
    document.add_heading("Material de apoyo", level=1)
    document.add_paragraph("Usar esta guía en la práctica.")
    document.save(source)
    snapshot = Snapshot.from_mapping({
        "courses": [{"id": "course-1", "course_id": "ELE1", "name": "Electrónica"}],
        "activities": [{
            "id": "content-1", "course_id": "course-1", "kind": "content", "title": "Lectura",
            "attachments": [{
                "id": "doc-1", "name": "Guía.docx",
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "source_url": "/bbcswebdav/pid-doc/xid-doc",
            }],
        }],
    })

    render_snapshot(snapshot, tmp_path, downloader=FakeDownloader(source.read_bytes()))
    sidecar = tmp_path / "Blackboard" / "ELE1" / "Contenido" / "Adjuntos" / "Guía--doc-1.docx.md"

    assert "# Material de apoyo" in sidecar.read_text(encoding="utf-8")
    assert "Usar esta guía en la práctica." in sidecar.read_text(encoding="utf-8")
