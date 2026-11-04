from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

_PRIVATE_LANES = {"Blackboard", "SINF", "ELE1", "ADCC", "LEMA", "Proyectos de Estudio", "Control Académico", ".blackboard-sync"}
_ALLOWED_ROOT_FILES = {"README.md", "ROADMAP.md", "LICENSE", ".gitignore", ".env.example"}
_ALLOWED_PROJECT_FILES = {"pyproject.toml", "README.md", "academic-workspace.example.json", "package.json", "pnpm-lock.yaml", "tsconfig.json"}

_PRIVATE_PATTERNS = (
    re.compile(r"[A-Z]:[\\/]Users[\\/][^\\/\r\n]+", re.IGNORECASE),
    re.compile(r"[A-Z]:[\\/](?:[^\\/\r\n]+[\\/]){2,}[^\s\"']+", re.IGNORECASE),
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?:\b(?:api[_-]?key|secret|password|cookie|token)\b|[\"'](?:api[_-]?key|secret|password|cookie|token)[\"'])\s*[:=]\s*[\"'][^\"'\r\n]{6,}[\"']", re.IGNORECASE),
)
_BACKSLASH = re.escape("\\")
_CODE_WINDOWS_USER_PATH = re.compile(
    r"[A-Z]:(?:" + _BACKSLASH + r"){1,2}Users(?:" + _BACKSLASH + r"){1,2}[\w.-]+",
    re.IGNORECASE,
)
_CODE_PRIVATE_PATTERNS = (
    _CODE_WINDOWS_USER_PATH,
    re.compile(r"[A-Z]:/Users/[^/\s\"']+", re.IGNORECASE),
    re.compile(r"[A-Z]:/(?:[^/\s\"']+/){2,}[^/\s\"']+", re.IGNORECASE),
    _PRIVATE_PATTERNS[2],
    _PRIVATE_PATTERNS[3],
)


@dataclass(frozen=True, slots=True)
class ExportResult:
    output: Path
    file_count: int


def _sanitize(text: str) -> str:
    safe_user_token = "__EXISTING_SAFE_USER_PLACEHOLDER__"
    safe_vault_token = "__EXISTING_SAFE_VAULT_PLACEHOLDER__"
    user_token = "__ACADEMIC_WORKSPACE_USER_PATH__"
    vault_token = "__ACADEMIC_WORKSPACE_VAULT_PATH__"
    text = text.replace("C:/Users/<user>", safe_user_token).replace("D:/path/to/vault", safe_vault_token)
    text = re.sub(r"[A-Z]:[\x5c/]Users[\x5c/][^\x5c/\s\"']+(?:[\x5c/][^\x5c/\s\"']+)?", user_token, text, flags=re.IGNORECASE)
    text = re.sub(r"[A-Z]:[\x5c/](?:[^\x5c/\r\n]+[\x5c/]){2,}[^\x5c/\s\"']+", vault_token, text, flags=re.IGNORECASE)
    return (
        text.replace(user_token, "C:/Users/<user>")
        .replace(vault_token, "D:/path/to/vault")
        .replace(safe_user_token, "C:/Users/<user>")
        .replace(safe_vault_token, "D:/path/to/vault")
    )


def _check_private(path: Path, text: str) -> None:
    inspected = text.replace("C:/Users/<user>", "").replace("D:/path/to/vault", "")
    code_suffixes = {".js", ".jsx", ".py", ".ts", ".tsx"}
    patterns = _CODE_PRIVATE_PATTERNS if path.suffix.lower() in code_suffixes else _PRIVATE_PATTERNS
    for pattern in patterns:
        if pattern.search(inspected):
            raise ValueError(f"private marker found in export candidate: {path}")


def _copy_text(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8")
    code_suffixes = {".js", ".jsx", ".py", ".ts", ".tsx"}
    sanitized = text if source.suffix.lower() in code_suffixes else _sanitize(text)
    _check_private(source, sanitized)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(sanitized, encoding="utf-8", newline="\n")


def _copy_candidate(project: Path, source: Path, destination: Path) -> None:
    project = project.resolve()
    resolved = source.resolve()
    if source.is_symlink() or project not in resolved.parents:
        raise ValueError(f"export candidate fuera del proyecto: {source}")
    payload = source.read_bytes()
    if any(byte < 32 and byte not in {9, 10, 13} for byte in payload):
        raise ValueError(f"archivo binario no permitido en export: {source}")
    try:
        payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"archivo binario no permitido en export: {source}") from error
    _copy_text(source, destination)


def _build_export(source: Path, output: Path) -> ExportResult:
    source = Path(source)
    output = Path(output)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    count = 0
    project = source / "academic-workspace"
    if not project.is_dir():
        raise ValueError("missing academic-workspace project")
    for relative in sorted(_ALLOWED_PROJECT_FILES):
        candidate = project / relative
        if candidate.is_file():
            _copy_candidate(project, candidate, output / "academic-workspace" / relative)
            count += 1
    for directory in ("src", "tests", "scripts", "prompts", "ui"):
        root = project / directory
        if not root.exists():
            continue
        for candidate in sorted(root.rglob("*")):
            if not candidate.is_file() or any(part in {"__pycache__", ".pytest_cache", ".venv", "dist"} for part in candidate.parts):
                continue
            relative = candidate.relative_to(project)
            _copy_candidate(project, candidate, output / "academic-workspace" / relative)
            count += 1
    template_files = {
        "README.md": "# Shareable Academic Workspace\n\nThis template contains code, synthetic fixtures and documentation only. It contains no LMS account, personal notes or credentials.\n",
        "LICENSE": "MIT License\n\nCopyright (c) 2026 Academic Workspace contributors\n\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the \\\"Software\\\"), to deal in the Software without restriction.\n",
        "PRIVACY.md": "# Privacy\n\nKeep LMS accounts, cookies, personal notes, assignments, feedback and third-party material private. This template contains synthetic fixtures only.\n",
        ".env.example": "# Credentials are configured outside the repository.\n# Do not put real secrets in this file.\n",
        "sources.example.json": json.dumps({"format": 1, "sources": [{"provider": "fixture", "instance": "demo", "root": "Fuentes/Fixture"}]}, indent=2) + "\n",
        ".gitignore": "Blackboard/\nFuentes/\nProyectos de Estudio/\nControl Académico/\n.blackboard-sync/\n.env\n.venv/\n__pycache__/\n.pytest_cache/\n",
    }
    for relative, content in template_files.items():
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")
        count += 1
    fixture = output / "fixtures" / "blackboard-synthetic" / "source.json"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text(json.dumps({
        "courses": [{"id": "course-1", "code": "DEMO", "name": "Curso sintético"}],
        "items": [{"id": "item-1", "course_id": "course-1", "kind": "assignment", "title": "Actividad sintética", "due_at": "2026-08-20T23:59:00Z"}],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    count += 1
    manifest = {
        "format": 1,
        "file_count": count + 1,
        "private_lanes_excluded": sorted(_PRIVATE_LANES),
        "source": "allowlist",
    }
    (output / "EXPORT-MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return ExportResult(output, count + 1)


def export_template(source: Path, output: Path) -> ExportResult:
    """Build an allowlisted export without leaving partial output on failure."""
    output = Path(output)
    staging = output.with_name(f".{output.name}.tmp-{uuid4().hex}")
    previous = output.with_name(f".{output.name}.previous-{uuid4().hex}")
    try:
        result = _build_export(Path(source), staging)
        if output.exists():
            output.replace(previous)
        try:
            staging.replace(output)
        except Exception:
            if previous.exists() and not output.exists():
                previous.replace(output)
            raise
        if previous.exists():
            try:
                shutil.rmtree(previous)
            except OSError:
                pass
        return ExportResult(output, result.file_count)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
