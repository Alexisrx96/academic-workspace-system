from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

_REGISTRY_RELATIVE = "Control Académico/Registro de resultados académicos.json"
_REPORT_RELATIVE = "Control Académico/Reporte de resultados académicos.md"
_STATUSES = {
    "pendiente",
    "entregado",
    "completado",
    "no_conformidad",
    "falta_preparacion",
    "no_entregado",
    "incompleto",
    "tarde",
    "en_revision",
    "resultado_desconocido",
}
_SCORE_ORIGINS = {"manual", "feedback_blackboard", "externo", "lider_grupo", "no_disponible"}


@dataclass(frozen=True, slots=True)
class AcademicResult:
    id: str
    course: str
    title: str
    kind: str
    status: str
    score: float | None
    score_origin: str
    score_visibility: str
    reason: str
    evidence: str
    source_ref: str
    action: str
    recommendation: str


def _empty_registry() -> dict[str, Any]:
    return {
        "schema": "academic-results.v1",
        "instructions": "Registro manual; no se completa desde calificaciones automáticas.",
        "items": [],
    }


def ensure_results_registry(target: Path) -> Path:
    path = Path(target) / _REGISTRY_RELATIVE
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_empty_registry(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def _load_registry(target: Path) -> tuple[Path, list[AcademicResult], list[str]]:
    path = ensure_results_registry(target)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Registro de resultados inválido: {path}") from error
    if not isinstance(payload, dict) or payload.get("schema") != "academic-results.v1":
        raise ValueError("El registro debe usar academic-results.v1")
    results: list[AcademicResult] = []
    errors: list[str] = []
    for index, raw in enumerate(payload.get("items", []), start=1):
        if not isinstance(raw, dict):
            errors.append(f"items[{index}] no es un objeto")
            continue
        status = str(raw.get("status", "resultado_desconocido"))
        origin = str(raw.get("score_origin", "no_disponible"))
        if status not in _STATUSES:
            errors.append(f"items[{index}].status inválido: {status}")
            continue
        if origin not in _SCORE_ORIGINS:
            errors.append(f"items[{index}].score_origin inválido: {origin}")
            continue
        score = raw.get("score")
        if score is not None:
            try:
                score = float(score)
            except (TypeError, ValueError):
                errors.append(f"items[{index}].score no es numérico")
                score = None
        results.append(AcademicResult(
            id=str(raw.get("id", f"item-{index}")),
            course=str(raw.get("course", "")),
            title=str(raw.get("title", "")),
            kind=str(raw.get("kind", "actividad")),
            status=status,
            score=score,
            score_origin=origin,
            score_visibility=str(raw.get("score_visibility", "unknown")),
            reason=str(raw.get("reason", "")),
            evidence=str(raw.get("evidence", "")),
            source_ref=str(raw.get("source_ref", "")),
            action=str(raw.get("action", "")),
            recommendation=str(raw.get("recommendation", "")),
        ))
    return path, sorted(results, key=lambda item: (item.course, item.kind, item.title, item.id)), errors


def _default_action(item: AcademicResult) -> str:
    actions = {
        "no_conformidad": "Revisar la rúbrica, identificar cada incumplimiento y rehacer un ejemplo equivalente.",
        "falta_preparacion": "Programar una sesión de preparación y resolver un ejercicio diagnóstico antes de la próxima entrega.",
        "no_entregado": "Confirmar la causa y establecer una entrega de recuperación o una fecha de seguimiento.",
        "incompleto": "Completar los componentes faltantes y verificar la rúbrica punto por punto.",
        "tarde": "Analizar el bloqueo de planificación y preparar la siguiente entrega con una fecha interna anterior.",
        "pendiente": "Verificar requisitos, fecha y próximo paso antes de reservar tiempo de estudio.",
        "en_revision": "Registrar el resultado cuando esté disponible; no asumir una calificación.",
        "resultado_desconocido": "Confirmar el resultado por la vía correspondiente, especialmente si fue una entrega grupal o externa.",
    }
    return actions.get(item.status, "")


def _is_actionable(item: AcademicResult) -> bool:
    return item.status in {"no_conformidad", "falta_preparacion", "no_entregado", "incompleto", "tarde", "pendiente"}


def _result_line(item: AcademicResult) -> str:
    score = "resultado no registrado" if item.score is None else f"resultado: {item.score:g} ({item.score_origin})"
    reason = f" · razón: {item.reason}" if item.reason else ""
    return f"- **{item.course} — {item.title}** ({item.kind}) · `{item.status}` · {score}{reason}"


def build_results_report(target: Path) -> str:
    path, items, errors = _load_registry(target)
    actionables = [item for item in items if _is_actionable(item)]
    recommendations = [item for item in items if not _is_actionable(item)]
    lines = [
        "# Reporte de resultados académicos",
        "",
        "> Registro separado de la sincronización. Las calificaciones no se obtienen ni se infieren automáticamente.",
        "> Los resultados pueden proceder de revisión manual, retroalimentación textual, una fuente externa o el líder de un grupo.",
        "",
        f"**Registro:** `{path.relative_to(target).as_posix()}` · **Elementos:** {len(items)}",
        "",
        "## Accionables de estudio y seguimiento",
        "",
    ]
    if actionables:
        for item in actionables:
            lines.append(_result_line(item))
            action = item.action or _default_action(item)
            if action:
                lines.append(f"  - **Acción:** {action}")
            if item.evidence:
                lines.append(f"  - **Evidencia:** {item.evidence}")
            if item.source_ref:
                lines.append(f"  - **Fuente:** {item.source_ref}")
            if item.score_visibility in {"group_leader_only", "external", "unknown"}:
                lines.append(f"  - **Visibilidad del resultado:** `{item.score_visibility}`; No se infiere una nota.")
    else:
        lines.append("> No hay accionables derivados de los resultados registrados.")
    lines.extend(["", "## Recomendaciones y resultados sin acción inmediata", ""])
    if recommendations:
        for item in recommendations:
            lines.append(_result_line(item))
            recommendation = item.recommendation or ("Conservar el ritmo y revisar el próximo hito." if item.status in {"entregado", "completado"} else _default_action(item))
            if recommendation:
                lines.append(f"  - **Recomendación:** {recommendation}")
            if item.score_visibility in {"group_leader_only", "external", "unknown"}:
                lines.append(f"  - **Visibilidad del resultado:** `{item.score_visibility}`; No se infiere una nota.")
    else:
        lines.append("> Aún no hay recomendaciones registradas.")
    lines.extend(["", "## Reglas de interpretación", "", "- Un resultado ausente no equivale a cero.", "- Una entrega grupal sin visibilidad individual queda como `resultado_desconocido` o `en_revision`.", "- Una no conformidad, falta de preparación, entrega incompleta o tardía genera un accionable; una entrega satisfactoria puede generar solo una recomendación.", "- La calificación solo se registra si se conoce su origen y visibilidad."])
    if errors:
        lines.extend(["", "## Errores del registro", "", *[f"- {error}" for error in errors]])
    return "\n".join(lines) + "\n"


def write_results_report(target: Path) -> Path:
    target = Path(target)
    report = target / _REPORT_RELATIVE
    content = build_results_report(target)
    report.parent.mkdir(parents=True, exist_ok=True)
    try:
        unchanged = report.read_text(encoding="utf-8") == content
    except OSError:
        unchanged = False
    if not unchanged:
        report.write_text(content, encoding="utf-8", newline="\n")
    return report


def result_actionables(target: Path) -> tuple[str, ...]:
    _path, items, _errors = _load_registry(target)
    return tuple(item.action or _default_action(item) for item in items if _is_actionable(item) and (item.action or _default_action(item)))


def result_attention_lines(target: Path) -> tuple[str, ...]:
    _path, items, _errors = _load_registry(target)
    return tuple(
        f"- [ ] **{item.course} — resultado {item.status}** · {item.title} — {item.action or _default_action(item)}"
        for item in items
        if _is_actionable(item)
    )
