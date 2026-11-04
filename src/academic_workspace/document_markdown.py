from __future__ import annotations

import json
from pathlib import Path
import re


_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _clean(value: str) -> str:
    return " ".join(value.split())


def _preserve_lines(value: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()]
    output: list[str] = []
    previous_blank = True
    for line in lines:
        if not line:
            if not previous_blank:
                output.append("")
            previous_blank = True
        else:
            output.append(line)
            previous_blank = False
    return "\n".join(output).strip()


def _docx_markdown(path: Path) -> tuple[str, str, str]:
    from docx import Document

    document = Document(path)
    title = path.stem
    blocks: list[str] = []
    found_title = False
    for paragraph in document.paragraphs:
        text = _clean(paragraph.text)
        if not text:
            continue
        style = paragraph.style.name.lower() if paragraph.style else ""
        if style.startswith("heading"):
            level = next((int(char) for char in style if char.isdigit()), 1)
            if not found_title and level == 1:
                title = text
                found_title = True
                continue
            blocks.append("#" * max(2, min(level, 6)) + " " + text)
        else:
            blocks.append(text)
    for table in document.tables:
        rows = [[_clean(cell.text).replace("|", "\\|") for cell in row.cells] for row in table.rows]
        if not rows:
            continue
        width = max(len(row) for row in rows)
        normalized = [row + [""] * (width - len(row)) for row in rows]
        blocks.append("| " + " | ".join(normalized[0]) + " |\n| " + " | ".join(["---"] * width) + " |")
        blocks.extend("| " + " | ".join(row) + " |" for row in normalized[1:])
    body = "\n\n".join(blocks) or "> El documento no contiene texto legible.\n"
    return title, body, "structured"


def _pdf_markdown(path: Path) -> tuple[str, str, str]:
    from pypdf import PdfReader

    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        try:
            text = page.extract_text(extraction_mode="layout", layout_mode_strip_rotated=False) or ""
        except TypeError:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append(_preserve_lines(text))
    if not any(pages):
        return path.stem, "> Este PDF no contiene una capa de texto; requiere OCR para extraer su contenido.\n", "ocr-required"
    body = "\n\n".join(
        f"## Página {index}\n\n{text}" if text else f"## Página {index}\n\n> Página sin texto extraíble."
        for index, text in enumerate(pages, start=1)
    )
    return path.stem, body + "\n", "text-layer"


def extract_to_markdown(path: Path, mime_type: str | None = None) -> str:
    """Return deterministic, structured Markdown from a local PDF or DOCX."""
    path = Path(path)
    suffix = path.suffix.lower()
    source_format = "pdf" if mime_type == "application/pdf" or suffix == ".pdf" else "docx"
    try:
        if source_format == "pdf":
            title, body, extraction = _pdf_markdown(path)
        elif mime_type == _DOCX_MIME or suffix == ".docx":
            title, body, extraction = _docx_markdown(path)
        else:
            raise ValueError(f"Formato no soportado para extracción Markdown: {path.name}")
    except Exception:
        title = path.stem
        body = "> No se pudo extraer el texto de este archivo; se conserva el original para revisión manual.\n"
        extraction = "failed"
    frontmatter = (
        "---\n"
        f"source_file: {json.dumps(path.name, ensure_ascii=False)}\n"
        f"source_format: {json.dumps(source_format)}\n"
        f"extraction: {json.dumps(extraction)}\n"
        "---\n\n"
    )
    return frontmatter + f"# {title}\n\n{body}"


def supports_markdown_extraction(path: Path, mime_type: str | None = None) -> bool:
    return mime_type in {"application/pdf", _DOCX_MIME} or Path(path).suffix.lower() in {".pdf", ".docx"}
