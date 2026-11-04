from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .live_browser import _candidate_profile_dirs
from .phs_tool import check_phs
from .source_config import SourceConfig, SourceConfigError, load_source_configs

_CONFIG_RELATIVE = ".blackboard-sync/workspace-config.json"


class WorkspaceConfigError(ValueError):
    """Raised when an explicit workspace configuration cannot be trusted."""


@dataclass(frozen=True, slots=True)
class StudyConfig:
    weekly_capacity_minutes: int = 600
    dashboard_action_limit: int = 8
    default_session_minutes: int = 25


@dataclass(frozen=True, slots=True)
class PrivacyConfig:
    allow_grade_import: bool = False
    allow_external_sources: bool = True
    preserve_manual_results: bool = True


@dataclass(frozen=True, slots=True)
class MemoryConfig:
    backend: str = "sqlite"
    database: str = ".blackboard-sync/memory.sqlite3"
    import_legacy_jsonl: bool = True


@dataclass(frozen=True, slots=True)
class ToolConfig:
    math_physics_engine: str = "phs"
    prefer_math_physics_verification: bool = True
    require_math_physics_verification: bool = False


@dataclass(frozen=True, slots=True)
class WorkspaceConfig:
    schema: str = "academic-workspace-config.v1"
    language: str = "es"
    timezone: str = "America/Guatemala"
    study: StudyConfig = StudyConfig()
    privacy: PrivacyConfig = PrivacyConfig()
    memory: MemoryConfig = MemoryConfig()
    tools: ToolConfig = ToolConfig()

    def to_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, "language": self.language, "timezone": self.timezone, "study": asdict(self.study), "privacy": asdict(self.privacy), "memory": asdict(self.memory), "tools": asdict(self.tools)}


def _path(target: Path) -> Path:
    return Path(target) / _CONFIG_RELATIVE


def default_config() -> WorkspaceConfig:
    return WorkspaceConfig()


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise WorkspaceConfigError("los valores de configuración booleanos deben ser true o false")
    return value


def load_workspace_config(target: Path) -> WorkspaceConfig:
    path = _path(target)
    if not path.is_file():
        return default_config()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise WorkspaceConfigError(f"workspace-config.json inválido: {error}") from error
    if not isinstance(payload, dict) or payload.get("schema") != "academic-workspace-config.v1":
        raise WorkspaceConfigError("workspace-config.json tiene un schema inválido")
    sections: dict[str, dict[str, Any]] = {}
    for name in ("study", "privacy", "memory", "tools"):
        value = payload.get(name)
        if value is None:
            sections[name] = {}
        elif isinstance(value, dict):
            sections[name] = value
        else:
            raise WorkspaceConfigError(f"workspace-config.json: {name} debe ser un objeto")
    study = sections["study"]
    privacy = sections["privacy"]
    memory = sections["memory"]
    tools = sections["tools"]
    return WorkspaceConfig(
        language=str(payload.get("language") or "es"),
        timezone=str(payload.get("timezone") or "America/Guatemala"),
        study=StudyConfig(
            weekly_capacity_minutes=int(study.get("weekly_capacity_minutes", 600)),
            dashboard_action_limit=int(study.get("dashboard_action_limit", 8)),
            default_session_minutes=int(study.get("default_session_minutes", 25)),
        ),
        privacy=PrivacyConfig(
            allow_grade_import=_coerce_bool(privacy.get("allow_grade_import"), False),
            allow_external_sources=_coerce_bool(privacy.get("allow_external_sources"), True),
            preserve_manual_results=_coerce_bool(privacy.get("preserve_manual_results"), True),
        ),
        memory=MemoryConfig(
            backend=str(memory.get("backend") or "sqlite"),
            database=str(memory.get("database") or ".blackboard-sync/memory.sqlite3"),
            import_legacy_jsonl=_coerce_bool(memory.get("import_legacy_jsonl"), True),
        ),
        tools=ToolConfig(
            math_physics_engine=str(tools.get("math_physics_engine") or "phs"),
            prefer_math_physics_verification=_coerce_bool(tools.get("prefer_math_physics_verification"), True),
            require_math_physics_verification=_coerce_bool(tools.get("require_math_physics_verification"), False),
        ),
    )


def validate_config(config: WorkspaceConfig) -> list[str]:
    errors: list[str] = []
    if config.language not in {"es", "en"}:
        errors.append("language debe ser es o en")
    if not config.timezone.strip():
        errors.append("timezone no puede estar vacío")
    if config.study.weekly_capacity_minutes < 0:
        errors.append("study.weekly_capacity_minutes no puede ser negativo")
    if config.study.dashboard_action_limit < 1:
        errors.append("study.dashboard_action_limit debe ser positivo")
    if config.study.default_session_minutes < 1:
        errors.append("study.default_session_minutes debe ser positivo")
    if config.memory.backend not in {"sqlite", "jsonl"}:
        errors.append("memory.backend debe ser sqlite o jsonl")
    if not config.memory.database.strip():
        errors.append("memory.database no puede estar vacío")
    if config.tools.math_physics_engine != "phs":
        errors.append("tools.math_physics_engine debe ser phs en esta versión")
    return errors


def write_workspace_config(target: Path, config: WorkspaceConfig | None = None) -> Path:
    path = _path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps((config or default_config()).to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def init_workspace(target: Path) -> dict[str, Any]:
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    config_path = _path(target)
    created: list[str] = []
    if not config_path.exists():
        write_workspace_config(target)
        created.append(config_path.relative_to(target).as_posix())
    sources_path = target / ".blackboard-sync/sources.json"
    if not sources_path.exists():
        source = SourceConfig("blackboard_ultra", "default", "Blackboard")
        sources_path.parent.mkdir(parents=True, exist_ok=True)
        sources_path.write_text(json.dumps({"format": 1, "sources": [asdict(source)]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        (target / source.root).mkdir(parents=True, exist_ok=True)
        created.append(sources_path.relative_to(target).as_posix())
    return {"schema": "workspace-init.v1", "target": target.as_posix(), "created": created, "changed": bool(created)}


def validate_workspace(target: Path) -> dict[str, Any]:
    target = Path(target)
    errors: list[str] = []
    try:
        config = load_workspace_config(target)
    except (WorkspaceConfigError, TypeError, ValueError) as error:
        config = default_config()
        errors.append(str(error))
    errors.extend(validate_config(config))
    try:
        sources = load_source_configs(target)
    except SourceConfigError as error:
        sources = ()
        errors.append(str(error))
    source_checks = [{"provider": source.provider, "instance": source.instance, "root": source.root, "exists": (target / source.root).is_dir()} for source in sources]
    errors.extend(f"source root no existe: {item['root']}" for item in source_checks if not item["exists"])
    return {"schema": "workspace-config-validation.v1", "valid": not errors, "errors": errors, "config": config.to_dict(), "sources": source_checks, "path": _path(target).relative_to(target).as_posix()}


def workspace_status(target: Path) -> dict[str, Any]:
    target = Path(target)
    state = target / ".blackboard-sync"
    health_path = state / "sync-health.json"
    try:
        health = json.loads(health_path.read_text(encoding="utf-8")) if health_path.is_file() else {}
    except json.JSONDecodeError:
        health = {}
    validation = validate_workspace(target)
    try:
        config = load_workspace_config(target)
    except (WorkspaceConfigError, TypeError, ValueError):
        config = default_config()
    return {"schema": "workspace-status.v1", "target": target.as_posix(), "config_valid": validation["valid"], "memory": {"backend": config.memory.backend, "database": config.memory.database, "exists": (target / config.memory.database).is_file() if not Path(config.memory.database).is_absolute() else Path(config.memory.database).is_file()}, "tools": {"phs": check_phs().to_dict()}, "sync_health": health, "sources": validation["sources"], "indexes": {"lexical": (state / "search.sqlite3").is_file(), "semantic": (state / "semantic-search.sqlite3").is_file(), "graph": (state / "resource-registry.sqlite3").is_file()}, "reports": {"weekly": (target / "Control Académico/Estado semanal.md").is_file(), "results": (target / "Control Académico/Reporte de resultados académicos.md").is_file(), "dashboard": (target / "Control Académico/00 - Dashboard académico.md").is_file()}}


def workspace_doctor(target: Path) -> dict[str, Any]:
    target = Path(target)
    validation = validate_workspace(target)
    state = target / ".blackboard-sync"
    checks = {
        "target_directory": target.is_dir(),
        "state_directory": state.is_dir(),
        "state_writable": state.is_dir() and bool(__import__("os").access(state, __import__("os").W_OK)),
        "config": validation["valid"],
        "devtools_candidates": len(_candidate_profile_dirs()),
        "lexical_index": (state / "search.sqlite3").is_file(),
        "graph_registry": (state / "resource-registry.sqlite3").is_file(),
        "phs_installed": check_phs().installed,
    }
    errors = list(validation["errors"])
    warnings: list[str] = []
    if not checks["phs_installed"]:
        warnings.append(check_phs().suggestion or "PHS no está instalado.")
    if not checks["target_directory"]:
        errors.append("target no existe")
    if not checks["state_writable"]:
        errors.append("state directory no escribible")
    return {"schema": "workspace-doctor.v1", "ok": not errors, "checks": checks, "errors": errors, "warnings": warnings, "status": workspace_status(target)}
