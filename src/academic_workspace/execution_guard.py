from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any

from .generation_report import ALLOWED_ROOTS, ALLOWED_ROOT_FILES, _allowed_roots


_BACKUP_ROOT = ".blackboard-sync/backups/latest"
_CONTROL_PREFIX = ".blackboard-sync/"


def _safe_relative(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"ruta insegura: {value}")
    return path


def create_backup(target: Path, paths: list[str]) -> Path:
    target = Path(target)
    backup = target / _BACKUP_ROOT
    if backup.exists():
        shutil.rmtree(backup)
    planned = sorted(set(paths))
    stored: list[str] = []
    for relative in planned:
        source = target / _safe_relative(relative)
        if not source.is_file():
            continue
        destination = backup / _safe_relative(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        stored.append(relative)
    backup.mkdir(parents=True, exist_ok=True)
    (backup / "manifest.json").write_text(
        json.dumps({"schema": "rollback-backup.v1", "paths": stored, "planned": planned}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return backup


def rollback_backup(target: Path, backup: Path | None = None) -> None:
    target = Path(target)
    backup = Path(backup) if backup else target / _BACKUP_ROOT
    payload = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    stored = {str(value) for value in payload.get("paths", []) if isinstance(value, str)}
    planned = {str(value) for value in payload.get("planned", stored) if isinstance(value, str)}
    for relative in planned - stored:
        destination = target / _safe_relative(relative)
        if destination.is_file():
            destination.unlink()
    for relative in stored:
        source = backup / _safe_relative(relative)
        destination = target / _safe_relative(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def verify_execution(target: Path, preview: list[dict[str, Any]]) -> dict[str, Any]:
    target = Path(target)
    try:
        report = json.loads((target / ".blackboard-sync/generation-report.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "execution-verification.v1", "status": "blocked", "unexpected_paths": ["generation-report.json"]}
    approved = {str(path) for group in preview for path in group.get("paths", [])}
    actual = {
        str(path)
        for key in ("created", "changed", "deleted")
        for path in report.get(key, [])
        if isinstance(path, str)
    }
    allowed_roots = _allowed_roots(target)
    unexpected = sorted(
        path for path in actual - approved
        if not path.startswith(_CONTROL_PREFIX)
        and path not in ALLOWED_ROOT_FILES
        and path.split("/", 1)[0] not in allowed_roots
    )
    unexpected.extend(str(path) for path in report.get("unexpected_paths", []) if isinstance(path, str))
    unexpected = sorted(set(unexpected))
    blocked = report.get("status") == "blocked" or bool(unexpected)
    return {
        "schema": "execution-verification.v1",
        "status": "blocked" if blocked else "verified",
        "unexpected_paths": unexpected,
        "approved_paths": sorted(approved),
        "observed_paths": sorted(actual),
    }
