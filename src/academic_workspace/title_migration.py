from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
from typing import Any

from .render import _safe_name


def _title_from_item(item: dict[str, Any]) -> str | None:
    paths = item.get("content_path") or []
    if not paths:
        return None
    parent = str(paths[-1])
    return parent.rsplit("--", 1)[0] if "--" in parent else parent


def migrate_ultra_document_body(vault: Path, *, source_root: str = "Blackboard", run_id: str) -> dict[str, Any]:
    vault = Path(vault)
    source_map_path = vault / ".blackboard-sync" / "source-map.json"
    payload = json.loads(source_map_path.read_text(encoding="utf-8"))
    quarantine = vault / "_backups" / "renamed-ultradocumentbody" / run_id
    moved = []
    skipped = []
    for item in payload.get("items", []):
        item_id = str(item.get("id", ""))
        note_path = str(item.get("note_path", ""))
        if not note_path.startswith(source_root.rstrip("/") + "/") or "ultraDocumentBody--" not in note_path:
            continue
        title = _title_from_item(item)
        if not title or not item_id:
            skipped.append(note_path)
            continue
        expected = vault / note_path
        expected = expected.with_name(f"{_safe_name(title)}--{_safe_name(item_id)}.md")
        candidates = sorted((vault / source_root).rglob(f"ultraDocumentBody--{item_id}.md"))
        candidates = [path for path in candidates if "_backups" not in path.parts]
        canonical = expected if expected.is_file() else None
        if canonical is None and candidates:
            preferred = next((path for path in candidates if path.parent == expected.parent), candidates[0])
            expected.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(preferred), str(expected))
            canonical = expected
            moved.append({"old_path": preferred.relative_to(vault).as_posix(), "new_path": expected.relative_to(vault).as_posix(), "sha256": sha256(expected.read_bytes()).hexdigest(), "title": title})
        if canonical is None:
            skipped.append(note_path)
            continue
        text = canonical.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"(?m)^#\s+ultraDocumentBody\s*$", f"# {title}", text)
        canonical.write_text(text, encoding="utf-8", newline="\n")
        for duplicate in candidates:
            if duplicate == canonical or not duplicate.exists():
                continue
            destination = quarantine / duplicate.relative_to(vault)
            destination.parent.mkdir(parents=True, exist_ok=True)
            digest = sha256(duplicate.read_bytes()).hexdigest()
            shutil.move(str(duplicate), str(destination))
            moved.append({"old_path": duplicate.relative_to(vault).as_posix(), "quarantine_path": destination.relative_to(vault).as_posix(), "sha256": digest, "title": title})
    manifest = {"schema": "ultradocumentbody-title-migration.v1", "run_id": run_id, "moved_count": len(moved), "skipped": skipped, "items": moved}
    quarantine.mkdir(parents=True, exist_ok=True)
    manifest_path = quarantine / "migration-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {**manifest, "manifest_path": manifest_path.relative_to(vault).as_posix()}
