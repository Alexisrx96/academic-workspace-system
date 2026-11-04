from __future__ import annotations

from typing import Callable, Any


_ALLOWED_ROOTS = {
    "Blackboard-UTEC", "02 - Cursos", "Control Académico", "Proyectos de Estudio",
    "06 - Ingeniería", ".blackboard-sync", ".obsidian", "_backups", "_exports",
    "docs", "academic-workspace", "skills",
}


def preview_confirmation_reasons(preview: list[dict[str, Any]]) -> list[str]:
    reasons: list[str] = []
    if any(item.get("operation") == "delete" and item.get("count", 0) for item in preview):
        reasons.append("eliminación de archivos")
    unexpected = []
    for item in preview:
        for path in item.get("paths", []):
            root = str(path).split("/", 1)[0]
            if "/" not in str(path) and root not in _ALLOWED_ROOTS and root != "README.md":
                unexpected.append(str(path))
    if unexpected:
        reasons.append("escrituras fuera de rutas permitidas: " + ", ".join(sorted(set(unexpected))))
    return reasons


def confirm_file_preview(
    preview: list[dict[str, Any]],
    *,
    approve: bool = False,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> bool:
    reasons = preview_confirmation_reasons(preview)
    if not reasons or approve:
        return True
    output_fn("La vista previa requiere confirmación: " + "; ".join(reasons) + ".")
    output_fn("Escribe 'si' para aplicar estos cambios; cualquier otra respuesta cancela.")
    try:
        answer = input_fn("> ")
    except (EOFError, KeyboardInterrupt):
        return False
    return answer.strip().casefold() in {"si", "sí", "yes", "y"}
