from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


_CONTROL = "Control Académico"
_CONFIG = "Mapa de cursos.json"
_GENERATED_MARKER = "generated_by: knowledge-bridge"


@dataclass(frozen=True, slots=True)
class KnowledgeBridgeResult:
    course_count: int
    map_path: Path
    config_path: Path


def _write_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if path.read_text(encoding="utf-8") == content:
            return
    except OSError:
        pass
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _workspace_default(course_code: str) -> str:
    return f"02 - Cursos/{course_code.split('-', 1)[0]}"


def _link(path: str, label: str) -> str:
    return f"[[{path.removesuffix('.md')}|{label}]]"


def _hub_path(workspace: Path) -> Path:
    primary = workspace / "00 - Blackboard y apuntes.md"
    if not primary.exists():
        return primary
    try:
        text = primary.read_text(encoding="utf-8")
    except OSError:
        return workspace / "00 - Blackboard y apuntes (generado).md"
    return primary if _GENERATED_MARKER in text else workspace / "00 - Blackboard y apuntes (generado).md"


def _personal_notes(target: Path, workspace: Path, hub: Path) -> list[str]:
    ignored = {hub.resolve()}
    result = []
    for path in sorted(workspace.rglob("*.md")):
        if path.resolve() in ignored or "skills" in path.relative_to(workspace).parts:
            continue
        relative = path.relative_to(target).as_posix()
        label = path.stem
        result.append(f"- {_link(relative, label)}")
    return result


def _course_hub(target: Path, course_code: str, source_path: str, workspace_path: str, *, source_provider: str, source_instance: str) -> Path:
    workspace = target / workspace_path
    workspace.mkdir(parents=True, exist_ok=True)
    hub = _hub_path(workspace)
    notes = _personal_notes(target, workspace, hub)
    frontmatter = [
        "---",
        _GENERATED_MARKER,
        f'course_code: "{course_code}"',
        f'source_provider: "{source_provider}"',
        f'source_instance: "{source_instance}"',
        f'source_ref: "{source_path}"',
    ]
    source_label = "fuente académica" if source_provider == "blackboard_ultra" else source_provider
    link_label = "Fuente académica" if source_provider == "blackboard_ultra" else "Fuente " + source_provider
    frontmatter.extend(["---", ""])
    lines = [
        *frontmatter,
        f"# {course_code}: apuntes y trabajos",
        "",
        f"> {source_label} conserva la fuente sincronizada. Esta carpeta conserva tus apuntes, borradores y entregables propios.",
        "",
        f"## Fuente {source_label}",
        "",
        f"- {_link(source_path + '/index', link_label + ': ' + course_code)}",
        "",
        "## Tus apuntes y trabajos",
        "",
    ]
    lines.extend(notes or ["> Aún no hay notas propias registradas en esta carpeta."])
    lines.extend([
        "",
        "## Cómo vincular un apunte nuevo",
        "",
        "Crea tu nota dentro de esta carpeta y añade una referencia explícita a la fuente:",
        "",
        "```yaml",
        f'source_blackboard: "{_link(source_path + "/index", course_code)}"',
        "```",
        "",
        "No se infieren relaciones por similitud de título: cada vínculo de estudio queda explícito y auditable.",
        "",
    ])
    _write_if_changed(hub, "\n".join(lines))
    return hub


def _template(control: Path) -> None:
    path = control / "Plantilla - Apunte vinculado.md"
    if path.exists():
        return
    _write_if_changed(path, """---
course: ""
note_kind: personal_note
source_provider: ""
source_instance: ""
source_ref: "[[Fuentes/.../index|Selecciona la fuente]]"
status: borrador
next_review: ""
---

# Tema

## Explicación en mis palabras

## Ejemplo o ejercicio propio

## Dudas y límites

## Próximo repaso
""")


def refresh_knowledge_bridge(target: Path) -> KnowledgeBridgeResult:
    target = Path(target)
    source_map = _load_json(target / ".blackboard-sync" / "source-map.json")
    if source_map is None or source_map.get("format") != 2 or not isinstance(source_map.get("courses"), list):
        raise ValueError("No existe un source-map Blackboard válido; ejecuta la sincronización primero.")
    control = target / _CONTROL
    config_path = control / _CONFIG
    existing = _load_json(config_path) or {}
    configured = existing.get("courses") if isinstance(existing.get("courses"), dict) else {}
    entries: list[dict[str, str]] = []
    for course in sorted(source_map["courses"], key=lambda item: str(item.get("course_code") or item.get("id") or "")):
        if not isinstance(course, dict):
            continue
        course_code = str(course.get("course_code") or course.get("id") or "")
        source_path = str(course.get("path") or "")
        if not course_code or not source_path:
            continue
        source_provider = str(course.get("source_provider") or "blackboard_ultra")
        source_instance = str(course.get("source_instance") or "default")
        prior = configured.get(course_code)
        if isinstance(prior, dict) and prior.get("workspace"):
            workspace = str(prior["workspace"])
        else:
            legacy = target / _workspace_default(course_code).split("/", 1)[-1]
            legacy_notes = [path for path in legacy.glob("*.md") if "generated_by: knowledge-bridge" not in path.read_text(encoding="utf-8", errors="replace")]
            workspace = legacy.name if legacy.exists() and legacy_notes else _workspace_default(course_code)
        hub = _course_hub(
            target,
            course_code,
            source_path,
            workspace,
            source_provider=source_provider,
            source_instance=source_instance,
        )
        entries.append({"course_code": course_code, "source_path": source_path, "workspace": workspace, "hub": hub.relative_to(target).as_posix(), "source_provider": source_provider, "source_instance": source_instance})
    config = {"format": 1, "courses": {entry["course_code"]: {"workspace": entry["workspace"]} for entry in entries}}
    _write_if_changed(config_path, json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    map_path = control / "Mapa de conocimiento.md"
    lines = [
        "# Mapa de conocimiento",
        "",
        "> Las fuentes académicas sincronizadas son de solo lectura. Las carpetas de curso en la raíz son tu espacio de apuntes, práctica y trabajos.",
        "",
        "## Cursos",
        "",
    ]
    for entry in entries:
        label = "fuente académica" if entry["source_provider"] == "blackboard_ultra" else entry["source_provider"]
        lines.append(f"- **{entry['course_code']}** ({label}): {_link(entry['source_path'] + '/index', 'Fuente académica' if entry['source_provider'] == 'blackboard_ultra' else 'Fuente ' + label)} ↔ {_link(entry['hub'], 'Apuntes y trabajos')}")
    lines.extend([
        "",
        "## Regla de vínculo",
        "",
        "Cada apunte propio debe llevar un campo `source_ref` con un wikilink a la fuente que lo originó. En notas Blackboard antiguas, `source_blackboard` se conserva como alias compatible.",
        "",
    ])
    _write_if_changed(map_path, "\n".join(lines))
    _template(control)
    return KnowledgeBridgeResult(len(entries), map_path, config_path)
