from __future__ import annotations

from pathlib import Path
from typing import Any

from .source_map import SourceMap


def _entries(source_map: SourceMap | None) -> dict[str, dict[str, Any]]:
    if source_map is None:
        return {}
    entries: dict[str, dict[str, Any]] = {}
    for course in source_map.payload.get("courses", []):
        if isinstance(course, dict) and isinstance(course.get("id"), str):
            entries[f"course:{course['id']}"] = course
    for item in source_map.payload.get("items", []):
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            key = f"item:{item.get('course_id')}:{item['id']}"
            entries[key] = item
    return entries


def _paths(entry: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    if "path" in entry and isinstance(entry["path"], str):
        paths.add(f"{entry['path'].rstrip('/')}/index.md")
    if isinstance(entry.get("note_path"), str):
        paths.add(entry["note_path"])
    for attachment in entry.get("attachments", []):
        if not isinstance(attachment, dict) or not isinstance(attachment.get("path"), str):
            continue
        path = attachment["path"]
        paths.add(path)
        if Path(path).suffix.lower() in {".pdf", ".docx"}:
            paths.add(path + ".md")
    return paths


def build_file_preview(current: SourceMap, previous: SourceMap | None, target: Path) -> list[dict[str, Any]]:
    """Return deterministic file operations without reading or writing source files."""
    current_entries = _entries(current)
    previous_entries = _entries(previous)
    groups: dict[str, set[str]] = {"create": set(), "update": set(), "delete": set()}

    for key, entry in current_entries.items():
        current_paths = _paths(entry)
        previous_entry = previous_entries.get(key)
        if previous_entry is None:
            groups["create"].update(current_paths)
            continue
        if previous_entry.get("fingerprint") != entry.get("fingerprint"):
            groups["update"].update(current_paths)
        else:
            groups["create"].update(
                path for path in current_paths if not (Path(target) / path).is_file()
            )

    for key, entry in previous_entries.items():
        if key not in current_entries:
            groups["delete"].update(_paths(entry))

    return [
        {"operation": operation, "count": len(paths), "paths": sorted(paths)}
        for operation, paths in groups.items()
        if paths
    ]
