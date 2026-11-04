from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Callable

from .canva_import import CanvaImportResult, fetch_canva_url, import_canva_html, is_canva_url

_URL_RE = re.compile(r"https?://(?:(?:www\.)?canva\.com|canva\.link)/[^\s<>)\]\"']+", re.IGNORECASE)
_STATE = ".blackboard-sync/canva-discovery.json"


@dataclass(frozen=True, slots=True)
class CanvaDiscoveryResult:
    discovered: int
    imported: tuple[CanvaImportResult, ...]
    skipped: int
    failed: tuple[dict[str, str], ...]


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"')
    return result


def _urls(text: str) -> tuple[str, ...]:
    found: list[str] = []
    for raw in _URL_RE.findall(text):
        url = raw.rstrip(".,;:!?'")
        if is_canva_url(url) and url not in found:
            found.append(url)
    return tuple(found)


def _load_state(target: Path) -> dict[str, dict[str, str]]:
    path = target / _STATE
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_state(target: Path, state: dict[str, dict[str, str]]) -> None:
    path = target / _STATE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _write_course_indexes(target: Path, source_root: str, state: dict[str, dict[str, str]]) -> None:
    grouped: dict[str, list[tuple[str, str]]] = {}
    for entry in state.values():
        note = entry.get("note", "")
        if entry.get("status") != "imported" or not note.startswith(f"{source_root}/"):
            continue
        relative = Path(note)
        parts = relative.parts
        if len(parts) < 4 or parts[2] != "Recursos Canva":
            continue
        course = parts[1]
        grouped.setdefault(course, []).append((relative.with_suffix("").as_posix(), relative.stem.split("--")[0]))
    marker_start = "<!-- academic-workspace:canva-start -->"
    marker_end = "<!-- academic-workspace:canva-end -->"
    for course, links in grouped.items():
        resource_dir = target / source_root / course / "Recursos Canva"
        resource_dir.mkdir(parents=True, exist_ok=True)
        lines = ["---", 'source_lane: "official"', 'resource_kind: "presentation-index"', f'source_course: "{course}"', "---", "", "# Presentaciones Canva", ""]
        for path, title in sorted(set(links), key=lambda item: (item[1].casefold(), item[0])):
            lines.append(f"- [[{Path(path).name}|{title}]]")
        lines.append("")
        (resource_dir / "index.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
        course_index = target / source_root / course / "index.md"
        if course_index.is_file():
            content = course_index.read_text(encoding="utf-8")
            block = f"{marker_start}\n\n## Presentaciones Canva\n\n- [[Recursos Canva/index|Ver presentaciones Canva]]\n\n{marker_end}"
            pattern = re.compile(re.escape(marker_start) + r".*?" + re.escape(marker_end), re.DOTALL)
            content = pattern.sub(block, content) if pattern.search(content) else content.rstrip() + "\n\n" + block + "\n"
            course_index.write_text(content, encoding="utf-8", newline="\n")

def discover_canva_presentations(
    target: Path,
    *,
    source_root: str = "Blackboard",
    fetcher: Callable[[str], str] | None = None,
    accessed_at: str | None = None,
    extra_observations: tuple[tuple[str, Path, dict[str, str]], ...] = (),
    on_progress: Callable[[str, int, int | None, str | None], None] | None = None,
) -> CanvaDiscoveryResult:
    """Discover Canva links in synchronized Blackboard notes and import new ones.

    Discovery is deterministic: the source note, course ID, URL and source-note
    hash form the stable observation. Failed imports remain retryable; unchanged
    observations are not fetched again.
    """
    target = Path(target)
    root = target / source_root
    state = _load_state(target)
    fetcher = fetcher or fetch_canva_url
    observed: dict[str, tuple[Path, dict[str, str], str]] = {}
    if root.is_dir():
        for path in sorted(root.rglob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            metadata = _frontmatter(text)
            for url in _urls(text):
                observed.setdefault(url, (path, metadata, sha256(text.encode("utf-8")).hexdigest()))
    for text, source, metadata in extra_observations:
        source_hash = sha256(text.encode("utf-8")).hexdigest()
        for url in _urls(text):
            observed.setdefault(url, (source, metadata, source_hash))
    imported: list[CanvaImportResult] = []
    failed: list[dict[str, str]] = []
    skipped = 0
    now = accessed_at or datetime.now(timezone.utc).isoformat()
    for index, (url, (source, metadata, source_hash)) in enumerate(observed.items(), start=1):
        if on_progress is not None:
            on_progress("canva", index, len(observed), None)
        previous = state.get(url, {})
        previous_note = target / previous.get("note", "") if previous.get("note") else None
        previous_has_slides = bool(previous_note and previous_note.is_file() and "slide_count:" in previous_note.read_text(encoding="utf-8", errors="replace") and "slide_layout: \"per-presentation\"" in previous_note.read_text(encoding="utf-8", errors="replace") and "ocr_backend:" in previous_note.read_text(encoding="utf-8", errors="replace"))
        if previous.get("status") == "imported" and previous.get("source_hash") == source_hash and previous.get("note", "").startswith(f"{source_root}/") and previous_has_slides:
            skipped += 1
            continue
        try:
            html = fetcher(url)
            course_path = source.relative_to(root).parts[0] if source.relative_to(root).parts else ""
            result = import_canva_html(
                html,
                target,
                source_url=url,
                accessed_at=now,
                related_courses=[metadata.get("course_code") or course_path or ""],
                course_path=course_path,
                source_root=source_root,
                source_course_id=metadata.get("source_course_id"),
                source_item_id=metadata.get("source_item_id"),
                source_ref=metadata.get("source_ref") or source.relative_to(target).as_posix(),
            )
            state[url] = {
                "status": "imported",
                "source": source.relative_to(target).as_posix(),
                "source_hash": source_hash,
                "content_hash": result.content_hash,
                "note": result.note.relative_to(target).as_posix(),
            }
            imported.append(result)
        except Exception as error:
            state[url] = {
                "status": "failed",
                "source": source.relative_to(target).as_posix(),
                "source_hash": source_hash,
                "error": str(error),
            }
            failed.append({"url": url, "error": str(error)})
    _save_state(target, state)
    _write_course_indexes(target, source_root, state)
    return CanvaDiscoveryResult(discovered=len(observed), imported=tuple(imported), skipped=skipped, failed=tuple(failed))
