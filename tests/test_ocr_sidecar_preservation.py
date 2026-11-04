from pathlib import Path

from pypdf import PdfWriter

from academic_workspace.models import Snapshot
from academic_workspace.render import render_snapshot


class FakeDownloader:
    def __init__(self, content: bytes):
        self.content = content

    def fetch(self, _source_url: str) -> bytes:
        return self.content


def test_renderer_preserves_existing_ocr_sidecar_for_unchanged_scanned_pdf(tmp_path: Path):
    pdf = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with pdf.open("wb") as stream:
        writer.write(stream)
    attachment_dir = tmp_path / "Blackboard" / "ELE1" / "Contenido" / "Adjuntos"
    attachment_dir.mkdir(parents=True)
    (attachment_dir / "guia--f1.pdf").write_bytes(pdf.read_bytes())
    sidecar = attachment_dir / "guia--f1.pdf.md"
    sidecar.write_text("# Archivo: guia--f1.pdf\n\nTexto obtenido por OCR.\n", encoding="utf-8")
    snapshot = Snapshot.from_mapping({
        "courses": [{"id": "c1", "course_id": "ELE1", "name": "Curso"}],
        "activities": [{
            "id": "a1", "course_id": "c1", "kind": "content", "title": "Guía",
            "attachments": [{"id": "f1", "name": "guia.pdf", "mime_type": "application/pdf", "source_url": "/bbcswebdav/a"}],
        }],
    })

    render_snapshot(snapshot, tmp_path, downloader=FakeDownloader(pdf.read_bytes()))

    assert "Texto obtenido por OCR." in sidecar.read_text(encoding="utf-8")
