from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .models import Snapshot
from .source_config import load_source_configs
from .source_map import build_source_map


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _document_format_error(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    suffix = ".pdf" if path.name.lower().endswith(".pdf.md") else ".docx"
    required = ("---\n", f'source_format: "{suffix[1:]}"\n', "extraction: ")
    if not text.startswith(required[0]) or any(value not in text for value in required[1:]) or "\n---\n\n# " not in text:
        return f"{path.as_posix()}: metadatos o título Markdown inválidos"
    return None


def validate_local_output(snapshot: Snapshot, target: Path) -> dict[str, Any]:
    target = Path(target)
    source = load_source_configs(target)[0]
    output = target / source.root
    source_map = build_source_map(
        snapshot,
        source_root=source.root,
        source_provider=source.provider,
        source_instance=source.instance,
    )
    map_path = target / ".blackboard-sync" / "source-map.json"
    try:
        stored_map = map_path.read_text(encoding="utf-8")
    except OSError:
        stored_map = ""
    files = sorted(path for path in output.rglob("*") if path.is_file())
    binaries = [path for path in files if "Adjuntos" in path.parts and path.suffix.lower() != ".md"]
    sidecars = [path for path in files if path.name.lower().endswith((".pdf.md", ".docx.md"))]
    expected_notes = [item["note_path"] for item in source_map.payload["items"]]
    expected_attachments = [attachment["path"] for item in source_map.payload["items"] for attachment in item["attachments"]]
    mapped_notes_missing = [path for path in expected_notes if not (target / path).is_file()]
    mapped_attachments_missing = [path for path in expected_attachments if not (target / path).is_file()]
    container_indexes_missing = [
        item["note_path"]
        for item in source_map.payload["items"]
        if item["is_container"] and (not item["note_path"].endswith("/index.md") or not (target / item["note_path"]).is_file())
    ]
    missing_content_notes = []
    for attachment in binaries:
        notes = [path for path in attachment.parent.parent.glob("*.md") if not path.name.lower().endswith((".pdf.md", ".docx.md"))]
        if not notes:
            missing_content_notes.append(_relative(attachment, target))
    missing_sidecars = [
        _relative(path, target)
        for path in binaries
        if path.suffix.lower() in {".pdf", ".docx"} and not Path(str(path) + ".md").is_file()
    ]
    document_format_errors = [
        message
        for path in sidecars
        if (message := _document_format_error(path)) is not None
    ]
    try:
        manifest = json.loads((target / ".blackboard-sync" / "manifest.json").read_text(encoding="utf-8"))
        entries = manifest["files"]
    except (OSError, json.JSONDecodeError, KeyError):
        entries = []
    manifest_hash_mismatches = [
        entry.get("path", "<ruta inválida>")
        for entry in entries
        if not isinstance(entry, dict)
        or not isinstance(entry.get("path"), str)
        or not isinstance(entry.get("sha256"), str)
        or not (target / entry["path"]).is_file()
        or sha256((target / entry["path"]).read_bytes()).hexdigest() != entry["sha256"]
    ]
    return {
        "source_map_matches_platform": stored_map == source_map.content,
        "source_map_contains_browser_url": any(marker in stored_map.lower() for marker in ("source_url", "download_url", "http://", "https://")),
        "mapped_notes_missing": mapped_notes_missing,
        "mapped_attachments_missing": mapped_attachments_missing,
        "container_indexes_missing": container_indexes_missing,
        "pdf_or_docx_without_sidecar": missing_sidecars,
        "document_format_errors": document_format_errors,
        "attachments_without_content_note": missing_content_notes,
        "manifest_hash_mismatches": manifest_hash_mismatches,
        "disk_markdown": sum(path.suffix.lower() == ".md" for path in files),
        "disk_attachments": len(binaries),
        "document_sidecars": len(sidecars),
        "manifest_entries": len(entries),
    }
