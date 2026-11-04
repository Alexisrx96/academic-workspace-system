from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil


_REQUIRED = (
    "resource_kind", "title", "author", "source_url", "license",
    "accessed_at", "related_courses", "related_topics", "curation_status",
)


@dataclass(frozen=True, slots=True)
class ExternalResourceResult:
    note: Path
    original: Path


class _HTMLText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


def _safe(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", value).strip().rstrip(".")
    return re.sub(r"\s+", " ", value) or "recurso"


def _body(source: Path) -> str:
    if source.suffix.lower() in {".html", ".htm"}:
        parser = _HTMLText()
        parser.feed(source.read_text(encoding="utf-8", errors="replace"))
        return parser.text()
    return source.read_text(encoding="utf-8", errors="replace")


def import_external_resource(source: Path, target: Path, metadata: dict) -> ExternalResourceResult:
    source = Path(source)
    target = Path(target)
    missing = [key for key in _REQUIRED if not metadata.get(key)]
    if missing:
        raise ValueError("missing external resource metadata: " + ", ".join(missing))
    if not source.is_file():
        raise FileNotFoundError(source)
    digest = sha256(source.read_bytes()).hexdigest()[:12]
    title = _safe(str(metadata["title"]))
    external_root = target / "Recursos Externos"
    note = external_root / f"{title}--{digest}.md"
    original = external_root / "Originales" / f"{digest}--{_safe(source.name)}"
    fields = {key: metadata[key] for key in _REQUIRED}
    frontmatter = "---\n" + "".join(f"{key}: {json.dumps(value, ensure_ascii=False)}\n" for key, value in fields.items()) + "---\n\n"
    content = frontmatter + f"# {metadata['title']}\n\n" + _body(source).strip() + "\n"
    note.parent.mkdir(parents=True, exist_ok=True)
    original.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(content, encoding="utf-8", newline="\n")
    if not original.exists():
        shutil.copyfile(source, original)
    return ExternalResourceResult(note=note, original=original)
