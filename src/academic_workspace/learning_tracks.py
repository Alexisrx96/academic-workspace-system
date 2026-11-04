from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re


def _path(target: Path, track_id: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,63}", track_id):
        raise ValueError("track_id debe ser slug seguro")
    return Path(target) / ".study-companion" / "tracks" / f"{track_id}.json"


def register_track(target: Path, track_id: str, title: str, kind: str, objectives: list[str], source_refs: list[str] | None = None) -> dict:
    path = _path(target, track_id)
    if path.exists():
        raise ValueError(f"el track ya existe: {track_id}")
    if not title or not kind or not objectives:
        raise ValueError("track requiere title, kind y objectives")
    track = {
        "schema": "learning-track.v1",
        "track_id": track_id,
        "title": title,
        "kind": kind,
        "objectives": objectives,
        "source_refs": source_refs or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(track, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return track


def list_tracks(target: Path) -> list[dict]:
    root = Path(target) / ".study-companion" / "tracks"
    result = []
    for path in sorted(root.glob("*.json")) if root.exists() else ():
        try:
            result.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return result
