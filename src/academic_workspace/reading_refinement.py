from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import re
import textwrap
import unicodedata
from .source_config import load_source_configs


STUDY_PROJECTS_DIR = "Proyectos de Estudio"
REFINED_READINGS_DIR = "Lecturas refinadas"

_STOP_WORDS = {
    "para", "como", "desde", "sobre", "entre", "donde", "cuando", "tener", "puede", "pueden",
    "este", "esta", "estos", "estas", "tambien", "porque", "todos", "todas", "cada", "solo",
    "datos", "informacion", "sistema", "sistemas", "clase", "lectura", "material", "document",
    "acuerdo", "ademas", "abierto", "ahora", "aplicar", "aplicaciones", "apoyar", "apoyo", "calidad",
    "caracteristicas", "cliente", "clientes", "comprender", "conocer", "crear", "cadena", "constante",
    "definicion", "asigna", "ejemplo", "ejemplos", "valor", "valores", "forma", "parte", "luego",
}


_TECHNICAL_BODY_MARKERS = ("ultradocumentbody", "documentbody")


@dataclass(frozen=True)
class Reading:
    course: Path
    source: Path
    title: str
    body: str
    tokens: frozenset[str]
    output_name: str


@dataclass(frozen=True)
class RefinementResult:
    root: Path
    course_count: int
    reading_count: int
    index_paths: tuple[Path, ...]


def _normalized(value: str) -> str:
    return "".join(character for character in unicodedata.normalize("NFD", value.lower()) if unicodedata.category(character) != "Mn")


def _course_code(course: Path) -> str:
    return course.name.split("-", 1)[0].upper()


def _strip_frontmatter(value: str) -> str:
    if value.startswith("---\n"):
        end = value.find("\n---\n", 4)
        if end >= 0:
            return value[end + 5 :].strip()
    return value.strip()


def _display_title(source: Path, body: str) -> str:
    heading = re.search(r"^#\s+(.+?)\s*$", body, flags=re.MULTILINE)
    title = heading.group(1).strip() if heading else source.stem
    title = re.sub(r"--_\d+_\d+", "", title).strip(" -._")
    if title.lower() in set(_TECHNICAL_BODY_MARKERS):
        title = re.sub(r"--_\d+_\d+$", "", source.parent.name).strip()
    return title or source.stem


def _source_body(value: str) -> str:
    body = _strip_frontmatter(value)
    body = re.sub(r"^#\s+.+?\s*$", "", body, count=1, flags=re.MULTILINE).strip()
    return body


def _tokens(value: str) -> frozenset[str]:
    values = re.findall(r"[a-záéíóúüñ]{5,}", _normalized(value))
    return frozenset(value for value in values if value not in _STOP_WORDS)


def _is_class_reading(source: Path, body: str) -> bool:
    if len(re.sub(r"\s+", "", body)) < 40:
        return False
    segments = [_normalized(part) for part in source.parts]
    joined = " / ".join(segments)
    has_class_context = any(marker in joined for marker in ("clase", "clases", "lectura", "lecturas", "material de estudio"))
    is_document_sidecar = source.name.lower().endswith((".pdf.md", ".docx.md"))
    is_plain_class_note = source.name.lower() != "index.md" and "adjuntos" not in {_normalized(part) for part in source.parts}
    is_content_body = any(source.name.lower().startswith(marker) for marker in _TECHNICAL_BODY_MARKERS) or is_document_sidecar or is_plain_class_note
    is_published_unit_document = is_document_sidecar and "unidad" in joined
    excluded = any(marker in joined for marker in ("asignacion", "actividad", "foro", "bienvenida", "indicaciones"))
    return (has_class_context and is_content_body or is_published_unit_document) and not excluded


def _safe_name(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*]', "", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value[:72] or "Lectura"


def _sentences(body: str) -> list[str]:
    compact = re.sub(r"\s+", " ", body).strip()
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿])", compact) if sentence.strip()]


def _sectioned(body: str) -> str:
    """Expose labels already present in compact Blackboard text as Markdown headings."""
    patterns = (
        r"^\s*(¿[^?\n]{3,100}\?)",
        r"(Características de [a-záéíóúüñ ]{2,80})(?=\s+[A-ZÁÉÍÓÚÑ])",
        r"(Ejemplo(?: empresarial| completo)?)(?=\s+[A-ZÁÉÍÓÚÑ])",
        r"(Relación entre [a-záéíóúüñ, ]{3,100})(?=\s+[A-ZÁÉÍÓÚÑ])",
        r"(Rectificación de (?:Media Onda|Onda Completa))",
        r"(Para el Semiciclo (?:Positivo|Negativo))",
        r"(Voltaje de Pico Inverso \(PIV\) o \(PRV\))",
        r"(Directiva (?:TEXTEQU|EQU))",
        r"(El operador DUP)",
        r"(Arreglo de (?:palabras|dobles palabras))",
    )
    rendered = body
    for pattern in patterns:
        rendered = re.sub(pattern, r"\n\n### \1\n\n", rendered, count=1)
    return re.sub(r"\n{3,}", "\n\n", rendered).strip()


def _summary_sentences(body: str) -> list[str]:
    without_headings = re.sub(r"^#{1,6}\s+.*$", "", body, flags=re.MULTILINE)
    return [sentence for sentence in _sentences(without_headings) if len(sentence) >= 35 and not sentence.startswith("[")]


def _format_attachment_blocks(body: str) -> str:
    def format_match(match: re.Match[str]) -> str:
        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", match.group(1))
        if not links:
            return match.group(0)
        return "## Adjuntos\n\n" + "\n".join(f"- [{label}]({target})" for label, target in links)

    return re.sub(r"^##\s+Adjuntos\s*(.*)$", format_match, body, flags=re.MULTILINE)


def _rewrite_relative_attachments(body: str, vault: Path, source: Path) -> str:
    def replace_link(match: re.Match[str]) -> str:
        label, target = match.group(1), re.sub(r"\s+", " ", match.group(2)).strip()
        if not target.startswith("Adjuntos/"):
            return match.group(0)
        destination = source.parent / target
        return f"[[{destination.relative_to(vault).as_posix()}|{label}]]"

    rendered = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, body)

    def replace_embed(match: re.Match[str]) -> str:
        target = re.sub(r"\s+", " ", match.group(1)).strip()
        if not target.startswith("Adjuntos/"):
            return match.group(0)
        destination = source.parent / target
        try:
            absolute = destination.relative_to(vault).as_posix()
        except ValueError:
            return match.group(0)
        return f"![[{absolute}]]"

    return re.sub(r"!\[\[([^\]]+)\]\]", replace_embed, rendered)


def _reflow(body: str, vault: Path, source: Path, width: int = 108) -> str:
    lines: list[str] = []
    prepared = _rewrite_relative_attachments(_format_attachment_blocks(body), vault, source)
    paragraphs = re.split(r"\n\s*\n", _sectioned(prepared))
    for paragraph in paragraphs:
        raw_lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        if raw_lines and all(line.startswith("- ") for line in raw_lines):
            lines.append("\n".join(raw_lines))
            continue
        compact = re.sub(r"\s+", " ", paragraph).strip()
        if not compact:
            continue
        if "![[" in compact or "[[" in compact:
            lines.append(compact)
        elif re.match(r"^#{1,6}\s+", compact):
            lines.append(compact)
        elif re.match(r"^(?:[-*+] |\d+[.)] )", compact):
            lines.append(compact)
        else:
            sentences = _sentences(compact)
            groups = [" ".join(sentences[index:index + 3]) for index in range(0, len(sentences), 3)] if len(sentences) > 3 else [compact]
            lines.append("\n\n".join(textwrap.fill(group, width=width, break_long_words=False, break_on_hyphens=False) for group in groups))
    return "\n\n".join(lines)


def _source_link(vault: Path, source: Path, source_label: str = "Blackboard") -> str:
    return f"[[{source.relative_to(vault).with_suffix('').as_posix()}|Abrir fuente {source_label}]]"


def _project_link(vault: Path, path: Path, label: str) -> str:
    # Generated derivative filenames include a source-path hash, so their bare names are vault-unique.
    return f"[[{path.stem}|{label}]]"


def _collect_readings(vault: Path, course: Path) -> list[Reading]:
    readings: list[Reading] = []
    for source in sorted(course.rglob("*.md"), key=lambda item: item.as_posix().lower()):
        value = source.read_text(encoding="utf-8", errors="replace")
        body = _source_body(value)
        if not _is_class_reading(source, body):
            continue
        title = _display_title(source, _strip_frontmatter(value))
        digest = hashlib.sha256(source.relative_to(vault).as_posix().encode("utf-8")).hexdigest()[:10]
        readings.append(Reading(course, source, title, body, _tokens(title + " " + body), f"{_safe_name(title)}--{digest}.md"))
    return readings


def _connections(reading: Reading, readings: list[Reading], vault: Path, destination: Path) -> list[str]:
    related: list[tuple[int, Reading]] = []
    for candidate in readings:
        if candidate.source == reading.source:
            continue
        shared = reading.tokens & candidate.tokens
        if len(shared) >= 2:
            related.append((len(shared), candidate))
    related.sort(key=lambda row: (-row[0], row[1].title.lower(), row[1].source.as_posix().lower()))
    if not related:
        return ["> No se encontró otra lectura de clase con al menos dos términos relevantes compartidos."]
    return [
        f"- {_project_link(vault, destination / candidate.output_name, candidate.title)} — coincidencia terminológica: {', '.join(sorted(reading.tokens & candidate.tokens)[:4])}."
        for _, candidate in related[:3]
    ]


def _render_reading(reading: Reading, readings: list[Reading], vault: Path, destination: Path, source_label: str = "Blackboard") -> str:
    rendered_body = _reflow(reading.body, vault, reading.source)
    summary_source = _rewrite_relative_attachments(reading.body, vault, reading.source)
    summary_source = re.sub(r"!\[\[.*?\]\]", "", summary_source, flags=re.DOTALL)
    sentences = _summary_sentences(summary_source)
    summary = sentences[:2] or ["> La fuente no contiene oraciones suficientes para un resumen extractivo."]
    return (
        f"# {reading.title}\n\n"
        "> Derivado de estudio legible. Refluye y organiza exclusivamente el texto publicado; no modifica la fuente ni añade contenido externo.\n\n"
        f"**Fuente:** {_source_link(vault, reading.source, source_label)}\n\n"
        "## Lectura refinada\n\n"
        f"{rendered_body}\n\n"
        "## Resumen del material\n\n"
        "> Resumen extractivo: conserva frases publicadas por la fuente y no agrega afirmaciones nuevas.\n\n"
        + "\n\n".join(f"- {sentence}" for sentence in summary)
        + "\n\n## Conexiones por estudiar\n\n"
        "> Enlaces calculados por términos compartidos en las lecturas publicadas; valida la relación durante tu estudio.\n\n"
        + "\n".join(_connections(reading, readings, vault, destination))
        + "\n"
    )


def _write_course(vault: Path, course: Path, source_label: str = "Blackboard") -> tuple[Path, int]:
    code = _course_code(course)
    destination = vault / STUDY_PROJECTS_DIR / f"{code} - Parcial 1" / REFINED_READINGS_DIR
    destination.mkdir(parents=True, exist_ok=True)
    readings = _collect_readings(vault, course)
    expected = {"00 - Índice de lecturas refinadas.md", *(reading.output_name for reading in readings)}
    for existing in destination.glob("*.md"):
        if existing.name not in expected:
            existing.unlink()
    for reading in readings:
        (destination / reading.output_name).write_text(_render_reading(reading, readings, vault, destination, source_label), encoding="utf-8", newline="\n")
    index_lines = [
        f"# {code} — Lecturas refinadas",
        "",
        "> Área derivada para lectura concentrada: las fuentes configuradas permanecen intactas y se abren únicamente cuando haga falta verificarlas.",
        "",
        "## Lecturas de clase",
        "",
    ]
    index_lines.extend(f"- {_project_link(vault, destination / reading.output_name, reading.title)}" for reading in readings)
    if not readings:
        index_lines.append("> No se detectaron lecturas de clase publicadas con texto suficiente."
        )
    index = destination / "00 - Índice de lecturas refinadas.md"
    index.write_text("\n".join(index_lines) + "\n", encoding="utf-8", newline="\n")
    return index, len(readings)


def build_refined_readings(vault: Path) -> RefinementResult:
    vault = Path(vault)
    source = load_source_configs(vault)[0]
    source_root = vault / source.root
    source_label = "académica" if source.provider == "blackboard_ultra" else source.provider
    courses = sorted((course for course in source_root.iterdir() if course.is_dir() and (course / "index.md").is_file()), key=lambda item: item.name)
    written = [_write_course(vault, course, source_label) for course in courses]
    return RefinementResult(
        root=vault / STUDY_PROJECTS_DIR,
        course_count=len(courses),
        reading_count=sum(count for _, count in written),
        index_paths=tuple(path for path, _ in written),
    )
