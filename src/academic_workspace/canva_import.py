from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

from .canva_ocr import extract_slide_text, write_slide_sidecar


@dataclass(frozen=True, slots=True)
class CanvaExtraction:
    title: str
    description: str
    body: str


@dataclass(frozen=True, slots=True)
class CanvaImportResult:
    note: Path
    original: Path
    content_hash: str
    slide_count: int = 0
    slide_paths: tuple[Path, ...] = ()


def is_canva_url(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    return host == "canva.com" or host.endswith(".canva.com") or host == "canva.link"


def _safe(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", value).strip().rstrip(".")
    return re.sub(r"\s+", " ", value) or "presentación Canva"


_SLIDE_URL_RE = re.compile(r"https://media\.canva\.com/v2/document-image/[^\"'<> ]+", re.IGNORECASE)


def slide_urls_from_html(html: str) -> tuple[str, ...]:
    found: list[str] = []
    for raw in _SLIDE_URL_RE.findall(html):
        url = unescape(raw)
        if url not in found:
            found.append(url)
    return tuple(found)


def _download_slide(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "UTEC-academic-workspace/0.1"})
    with urlopen(request, timeout=45) as response:
        return response.read()


class _CanvaParser(HTMLParser):
    _SKIP = {"script", "style", "noscript", "svg", "nav", "header", "footer"}
    _BLOCKS = {"p", "li", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "br"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.current_tag: str | None = None
        self.parts: list[tuple[str, str]] = []
        self.meta: dict[str, str] = {}
        self.title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self._SKIP:
            self.skip_depth += 1
        if tag == "meta":
            values = {key.lower(): value or "" for key, value in attrs}
            key = values.get("property") or values.get("name")
            if key in {"og:title", "og:description", "description"}:
                self.meta[key] = values.get("content", "")
        if tag == "title":
            self.current_tag = "title"
        elif self.skip_depth == 0 and tag in self._BLOCKS:
            self.current_tag = tag
            if tag == "br":
                self.parts.append(("text", "\n"))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.current_tag == tag:
            self.current_tag = None
        if tag in self._SKIP and self.skip_depth:
            self.skip_depth -= 1
        if self.skip_depth == 0 and tag in self._BLOCKS and tag != "br":
            self.parts.append(("text", "\n"))

    def handle_data(self, data: str) -> None:
        if self.current_tag == "title":
            self.title_parts.append(data)
        elif self.skip_depth == 0 and data.strip():
            self.parts.append(("heading" if (self.current_tag or "").startswith("h") else "text", data))


def _clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def extract_canva_html(html: str) -> CanvaExtraction:
    parser = _CanvaParser()
    parser.feed(html)
    title = _clean_line(parser.meta.get("og:title") or " ".join(parser.title_parts))
    if not title:
        title = "Presentación Canva"
    description = _clean_line(parser.meta.get("og:description") or parser.meta.get("description", ""))
    lines: list[str] = []
    pending = ""
    for kind, value in parser.parts:
        if value == "\n":
            if pending:
                lines.append(("# " if kind == "heading" else "") + pending)
                pending = ""
            continue
        cleaned = _clean_line(value)
        if not cleaned:
            continue
        if pending and kind == "heading":
            lines.append(pending)
            pending = cleaned
        else:
            pending = f"{pending} {cleaned}".strip()
    if pending:
        lines.append(pending)
    # Keep order while avoiding repeated DOM fragments and generic Canva chrome.
    seen: set[str] = set()
    body_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.lower() in {"canva", "diseñado con canva", "presentación"} or line in seen:
            continue
        seen.add(line)
        body_lines.append(line)
    body = "\n\n".join(body_lines) or "> No se encontró texto visible extraíble en la presentación.\n"
    return CanvaExtraction(title=title, description=description, body=body + "\n")


def import_canva_html(
    html: str,
    target: Path,
    *,
    source_url: str,
    accessed_at: str,
    related_courses: list[str] | tuple[str, ...] = (),
    related_topics: list[str] | tuple[str, ...] = (),
    license_name: str = "shared-canva-content; verify permissions",
    course_path: str | None = None,
    source_root: str = "Blackboard-UTEC",
    source_course_id: str | None = None,
    source_item_id: str | None = None,
    source_ref: str | None = None,
) -> CanvaImportResult:
    if not is_canva_url(source_url):
        raise ValueError("source_url debe pertenecer a canva.com")
    extraction = extract_canva_html(html)
    target = Path(target)
    digest = sha256(html.encode("utf-8")).hexdigest()[:12]
    root = target / source_root / course_path / "Recursos Canva" if course_path else target / "Recursos Externos" / "Canva"
    note = root / f"{_safe(extraction.title)}--{digest}.md"
    original = root / "Originales" / f"{digest}--presentation.html"
    fields = (
        ("resource_kind", "presentation"),
        ("source_provider", "canva"),
        ("title", extraction.title),
        ("author", "unknown"),
        ("source_url", source_url),
        ("license", license_name),
        ("accessed_at", accessed_at),
        ("related_courses", list(related_courses)),
        ("related_topics", list(related_topics)),
        ("curation_status", "imported"),
        ("content_hash", digest),
        ("extraction", "visible-html"),
    )
    if course_path:
        fields += (
            ("source_lane", "official"),
            ("source_course_id", source_course_id or ""),
            ("source_item_id", source_item_id or ""),
            ("source_ref", source_ref or ""),
        )
    frontmatter = "---\n" + "".join(
        f"{key}: {json.dumps(value, ensure_ascii=False)}\n" for key, value in fields
    ) + "---\n\n"
    note.parent.mkdir(parents=True, exist_ok=True)
    original.parent.mkdir(parents=True, exist_ok=True)
    if not original.exists() or sha256(original.read_bytes()).hexdigest()[:12] != digest:
        original.write_text(html, encoding="utf-8", newline="\n")
    slide_urls = slide_urls_from_html(html)
    slide_paths: list[Path] = []
    slides_dir = root / "Diapositivas" / digest
    for number, url in enumerate(slide_urls, start=1):
        slide_path = slides_dir / f"slide-{number:03d}.png"
        try:
            if not slide_path.exists():
                slide_path.parent.mkdir(parents=True, exist_ok=True)
                slide_path.write_bytes(_download_slide(url))
            slide_paths.append(slide_path)
        except Exception:
            continue
    ocr_sidecars: list[Path] = []
    ocr_available = True
    for number, image in enumerate(slide_paths, start=1):
        try:
            lines = extract_slide_text(image)
            relative_image = f"Diapositivas/{digest}/{image.name}"
            ocr_sidecars.append(write_slide_sidecar(image, number=number, lines=lines, relative_image=relative_image))
        except RuntimeError:
            ocr_available = False
            break
        except Exception:
            relative_image = f"Diapositivas/{digest}/{image.name}"
            ocr_sidecars.append(write_slide_sidecar(image, number=number, lines=(), relative_image=relative_image))
    fields += (
        ("slide_count", len(slide_paths)),
        ("slide_extraction", "document-image" if slide_urls else "none"),
        ("slide_layout", "per-presentation"),
        ("ocr_backend", "rapidocr-onnxruntime" if ocr_available and slide_paths else "unavailable"),
    )
    frontmatter = "---\n" + "".join(
        f"{key}: {json.dumps(value, ensure_ascii=False)}\n" for key, value in fields
    ) + "---\n\n"
    if extraction.description:
        body = f"> {extraction.description}\n\n{extraction.body}"
    else:
        body = extraction.body
    if slide_paths:
        body += "\n## Diapositivas\n\n" + "\n".join(
            f"### Diapositiva {index}\n\n[[Diapositivas/{digest}/{path.stem}|Texto OCR y diapositiva]]"
            for index, path in enumerate(slide_paths, start=1)
        ) + "\n"
    note.write_text(frontmatter + f"# {extraction.title}\n\n" + body, encoding="utf-8", newline="\n")
    return CanvaImportResult(note=note, original=original, content_hash=digest, slide_count=len(slide_paths), slide_paths=tuple(slide_paths))


def fetch_canva_url(url: str, profile_dir: Path | None = None) -> str:
    """Load a shared Canva presentation through an existing DevTools browser session.

    Authentication remains manual. The function only reads the rendered page and
    never submits credentials or attempts to bypass a sharing restriction.
    """
    if not is_canva_url(url):
        raise ValueError("La URL no pertenece a canva.com")
    try:
        from playwright.sync_api import sync_playwright
    except Exception as error:
        raise RuntimeError("Instala el extra browser para importar Canva desde una URL.") from error
    profiles = [Path(profile_dir)] if profile_dir else []
    if not profiles:
        home = Path.home()
        for root in (
            home / "AppData/Local/CuaDriver/BrowserProfiles",
            home / "AppData/Local/Google/Chrome/User Data",
        ):
            if root.is_dir():
                profiles.extend([root, *sorted(path for path in root.iterdir() if path.is_dir())])
    with sync_playwright() as playwright:
        for profile in profiles:
            try:
                port = (profile / "DevToolsActivePort").read_text(encoding="utf-8").splitlines()[0].strip()
                browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                if not browser.contexts:
                    continue
                context = browser.contexts[0]
                page = context.new_page()
                page.goto(url, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(1500)
                html = page.content()
                page.close()
                return html
            except Exception:
                continue
    raise RuntimeError("No se encontró una sesión DevTools disponible para leer Canva.")


def import_canva_file(source: Path, target: Path, **metadata: object) -> CanvaImportResult:
    source = Path(source)
    if source.suffix.lower() not in {".html", ".htm"}:
        raise ValueError("El archivo Canva debe ser HTML guardado desde una presentación compartida.")
    return import_canva_html(source.read_text(encoding="utf-8", errors="replace"), target, **metadata)
