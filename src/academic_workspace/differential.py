from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from .models import Snapshot
from .source_map import SourceMap, build_source_map, diff_source_maps


@dataclass(frozen=True, slots=True)
class DifferentialCheck:
    source_map: SourceMap
    diff: dict[str, int]
    integrity_ok: bool
    no_download_needed: bool


def _load_source_map(path: Path) -> SourceMap | None:
    try:
        content = path.read_text(encoding="utf-8")
        payload = json.loads(content)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("format") != 2 or payload.get("output_format") != 2:
        return None
    return SourceMap(payload=payload, content=content)


def _manifest_is_valid(target: Path, expected_snapshot_sha256: str) -> bool:
    try:
        manifest = json.loads((target / ".blackboard-sync" / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if manifest.get("snapshot_sha256") != expected_snapshot_sha256:
        return False
    entries = manifest.get("files")
    if not isinstance(entries, list):
        return False
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str) or not isinstance(entry.get("sha256"), str):
            return False
        path = target / entry["path"]
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            return False
    return True


def check_differential(
    snapshot: Snapshot,
    target: Path,
    *,
    source_root: str = "Blackboard",
    source_provider: str = "blackboard_ultra",
    source_instance: str = "default",
) -> DifferentialCheck:
    target = Path(target)
    current = build_source_map(
        snapshot,
        source_root=source_root,
        source_provider=source_provider,
        source_instance=source_instance,
    )
    previous = _load_source_map(target / ".blackboard-sync" / "source-map.json")
    diff = diff_source_maps(current, previous)
    integrity_ok = _manifest_is_valid(target, current.snapshot_sha256)
    no_download_needed = diff == {"added": 0, "changed": 0, "removed": 0} and integrity_ok
    return DifferentialCheck(
        source_map=current,
        diff=diff,
        integrity_ok=integrity_ok,
        no_download_needed=no_download_needed,
    )
