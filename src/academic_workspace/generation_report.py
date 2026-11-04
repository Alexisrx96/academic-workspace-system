from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .source_config import load_source_configs

ALLOWED_ROOTS = ("Blackboard-UTEC", "02 - Cursos", "Control Académico", "Proyectos de Estudio", "06 - Ingeniería", "Adjuntos", "Recursos Externos", ".blackboard-sync", ".hermes", ".study-companion", ".obsidian", "_backups", "_exports", "docs", "academic-workspace", "skills")
ALLOWED_ROOT_FILES = {".gitignore", ".study-companion.example.json", "00 - Navegación global.md", "01 - Fuentes académicas.md", "README.md", "ROADMAP.md", "PRIVACY.md", "LICENSE", "COMPOSABLE-COMPANION.md", "DETERMINISTIC-STANDARDS.md", "LEARNING-MODEL.md", "PHASE3-AUDIT.md", "PHYSURE_LANGUAGE_GUIDE.md", "IDEA.md", "Bienvenido.md"}


def _allowed_roots(target: Path) -> set[str]:
    configured = {source.root.split("/", 1)[0] for source in load_source_configs(target)}
    return set(ALLOWED_ROOTS) | configured


def _files(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if not path.is_file() or any(part in {"__pycache__", ".git"} for part in relative.parts):
            continue
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            result[relative.as_posix()] = {"size": path.stat().st_size, "sha256": digest}
        except OSError:
            continue
    return result


def capture_generation_baseline(target: Path) -> dict[str, Any]:
    """Capture files before this execution starts writing."""
    return {"files": _files(Path(target))}


def _fingerprint(value: Any) -> tuple[Any, Any]:
    """Read current and legacy report entries using one comparable shape."""
    if isinstance(value, dict):
        return value.get("size"), value.get("sha256")
    # Reports created before schema v1.1 stored only the file size.
    try:
        return int(value), None
    except (TypeError, ValueError):
        return value, None


def _changed(current: Any, previous: Any) -> bool:
    current_size, current_hash = _fingerprint(current)
    previous_size, previous_hash = _fingerprint(previous)
    if current_size != previous_size:
        return True
    # A legacy entry has no trustworthy content hash. Same-size content changes
    # become detectable as soon as the first v1.1 report is written.
    return previous_hash is not None and current_hash != previous_hash


def build_generation_report(target: Path, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    target = Path(target)
    allowed_roots = _allowed_roots(target)
    current = _files(target)
    current.pop(".blackboard-sync/generation-report.json", None)
    before = dict((previous or {}).get("files", {}))
    before.pop(".blackboard-sync/generation-report.json", None)
    created = sorted(set(current) - set(before))
    deleted = sorted(set(before) - set(current))
    changed = sorted(
        path for path in set(current) & set(before)
        if _changed(current[path], before[path])
    )
    root_writes = sorted(path for path in created + changed if "/" not in path and path != "README.md")
    unexpected = sorted(
        path for path in created + changed + deleted
        if path.split("/", 1)[0] not in allowed_roots and path not in ALLOWED_ROOT_FILES
    )
    return {
        "schema": "generation-report.v1.1",
        "status": "blocked" if unexpected else "safe",
        "created": created,
        "changed": changed,
        "deleted": deleted,
        "root_writes": root_writes,
        "unexpected_paths": unexpected,
        "files": current,
        "counts": {
            "created": len(created),
            "changed": len(changed),
            "deleted": len(deleted),
            "unexpected": len(unexpected),
        },
    }


def write_generation_report(target: Path, *, previous: dict[str, Any] | None = None) -> Path:
    target = Path(target)
    path = target / ".blackboard-sync/generation-report.json"
    if previous is None:
        previous = {}
        if path.exists():
            try:
                previous = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                previous = {}
    report = build_generation_report(target, previous)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path
