from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
from typing import Any


def _lane(relative: str) -> str:
    if relative.startswith("Blackboard/"):
        return "official"
    if relative.startswith("Recursos Externos/"):
        return "external"
    if relative.startswith("Control Académico/"):
        return "control"
    if relative.startswith(".blackboard-sync/") or relative.startswith(".obsidian/"):
        return "generated"
    return "work"


def _semantic_body(text: str) -> str:
    body = text
    if text.startswith("---\n") and "\n---\n" in text[4:]:
        body = text[text.find("\n---\n", 4) + 5 :]
    lines = []
    for line in body.splitlines():
        value = line.strip()
        if not value or re.match(r"^#{1,6}\s*.*$", value):
            continue
        lines.append(value)
    return " ".join(lines).strip()


def audit_empty_notes(target: Path, *, near_empty_chars: int = 0) -> dict[str, Any]:
    target = Path(target)
    items = []
    for path in sorted(target.rglob("*.md")):
        relative = path.relative_to(target).as_posix()
        if relative.startswith(".obsidian/") or relative.startswith("_backups/"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        semantic = _semantic_body(text)
        if len(semantic) > near_empty_chars:
            continue
        has_descendants = (
            path.name.lower() == "index.md"
            and any(child != path for child in path.parent.iterdir())
        ) or path.with_suffix("").is_dir()
        lane = _lane(relative)
        if has_descendants and lane == "official":
            action = "preserve_container"
        else:
            action = "review_leaf"
        items.append({
            "path": relative,
            "lane": lane,
            "bytes": path.stat().st_size,
            "title_only": bool(semantic == "" and text.strip()),
            "zero_bytes": path.stat().st_size == 0,
            "semantic_chars": len(semantic),
            "has_descendants": has_descendants,
            "action": action,
        })
    summary = {
        "candidates": len(items),
        "by_lane": {},
        "by_action": {},
        "zero_bytes": sum(item["zero_bytes"] for item in items),
    }
    for item in items:
        summary["by_lane"][item["lane"]] = summary["by_lane"].get(item["lane"], 0) + 1
        summary["by_action"][item["action"]] = summary["by_action"].get(item["action"], 0) + 1
    return {"schema": "empty-notes-audit.v1", "summary": summary, "items": items}


def write_empty_notes_audit(target: Path, output: Path | None = None, *, near_empty_chars: int = 0) -> Path:
    target = Path(target)
    output = Path(output) if output else target / "Control Académico" / "Auditorías" / "empty-notes-audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit_empty_notes(target, near_empty_chars=near_empty_chars), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return output


def quarantine_empty_notes(target: Path, prefix: str, *, run_id: str) -> dict[str, Any]:
    target = Path(target)
    prefix = prefix.strip("/").replace("\\", "/")
    candidates = [item for item in audit_empty_notes(target)["items"] if item["path"].startswith(prefix + "/") and item["action"] == "review_leaf"]
    backup_root = target / "_backups" / "pruned-empty" / run_id
    moved = []
    for item in candidates:
        source = target / item["path"]
        if not source.is_file():
            continue
        destination = backup_root / item["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest = sha256(source.read_bytes()).hexdigest()
        shutil.move(str(source), str(destination))
        moved.append({**item, "sha256": digest, "quarantine_path": destination.relative_to(target).as_posix()})

    prefix_root = target / prefix
    removed_dirs = []
    if prefix_root.exists():
        for directory in sorted((path for path in prefix_root.rglob("*") if path.is_dir()), key=lambda p: len(p.parts), reverse=True):
            if not any(directory.iterdir()):
                removed_dirs.append(directory.relative_to(target).as_posix())
                directory.rmdir()
    manifest = {
        "schema": "empty-notes-prune.v1",
        "prefix": prefix,
        "run_id": run_id,
        "moved_count": len(moved),
        "removed_empty_directories": removed_dirs,
        "items": moved,
    }
    manifest_path = backup_root / "prune-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {**manifest, "manifest_path": manifest_path.relative_to(target).as_posix()}
