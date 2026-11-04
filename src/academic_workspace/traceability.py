from __future__ import annotations

import json
from pathlib import Path
import re


def _frontmatter(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip('"')
    return values


def _course_map(target: Path) -> dict[str, str]:
    try:
        payload = json.loads((target / "Control Académico" / "Mapa de cursos.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    courses = payload.get("courses") if isinstance(payload, dict) else None
    if not isinstance(courses, dict):
        return {}
    return {
        str(code): str(value["workspace"])
        for code, value in courses.items()
        if isinstance(value, dict) and isinstance(value.get("workspace"), str)
    }


def _is_auditable(path: Path, metadata: dict[str, str], workspace: Path) -> bool:
    if "generated_by" in metadata:
        return False
    if path.name.startswith("00 - Blackboard y apuntes"):
        return False
    if "Lecturas refinadas" in path.relative_to(workspace).parts:
        return False
    return True


def build_traceability_report(target: Path) -> str:
    target = Path(target)
    course_map = _course_map(target)
    lines = [
        "# Reporte de trazabilidad académica",
        "",
        "> Vista generada. No modifica apuntes ni trabajos propios. Una nota es auditable cuando declara `note_kind` y una fuente mediante `source_ref` o el alias legacy `source_blackboard`.",
        "",
    ]
    if not course_map:
        lines.append("> No existe un mapa de cursos editable o no contiene workspaces auditables.")
        return "\n".join(lines) + "\n"
    for course_code, workspace_name in sorted(course_map.items()):
        workspace = target / workspace_name
        notes = []
        if workspace.exists():
            for path in sorted(workspace.rglob("*.md")):
                metadata = _frontmatter(path)
                if _is_auditable(path, metadata, workspace):
                    notes.append((path, metadata))
        linked = sum(bool(metadata.get("source_ref") or metadata.get("source_blackboard")) for _, metadata in notes)
        unlinked = len(notes) - linked
        classified = sum(bool(metadata.get("note_kind")) for _, metadata in notes)
        lines.extend([
            f"## {course_code}",
            "",
            f"- Workspace: `{workspace_name}`",
            f"- Notas auditables: {len(notes)}",
            f"- Con fuente explícita: {linked}",
            f"- Sin fuente explícita: {unlinked}",
            f"- Con `note_kind`: {classified}",
            "",
        ])
        if notes:
            lines.extend([
                "| Nota | note_kind | Fuente | Estado |",
                "|---|---|---|---|",
            ])
            for path, metadata in notes:
                source = metadata.get("source_ref") or metadata.get("source_blackboard") or "—"
                kind = metadata.get("note_kind") or "sin clasificar"
                state = "trazable" if source != "—" else "requiere vínculo"
                lines.append(f"| `{path.relative_to(target).as_posix()}` | `{kind}` | {source} | {state} |")
            lines.append("")
    return "\n".join(lines) + "\n"
