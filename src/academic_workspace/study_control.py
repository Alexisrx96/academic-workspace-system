from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from .assessment import build_diagnostic_comparison
from .academic_results import result_attention_lines, write_results_report
from .source_config import SourceConfig, load_source_configs
from .traceability import build_traceability_report
from .models import _normalize_activity_title


_CONTROL_DIRECTORY = "Control Académico"
_STATE_PATH = ".blackboard-sync/study-control-state.json"
_HEALTH_PATH = ".blackboard-sync/sync-health.json"
_HEALTH_FORMAT = 1
_SPANISH_MONTHS = "enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre"
_DATE_MENTION_RE = re.compile(
    rf"\b(?:(?:lunes|martes|miércoles|jueves|viernes|sábado|domingo)\s+)?"
    rf"\d{{1,2}}\s+de\s+(?:{_SPANISH_MONTHS})(?:\s+de\s+\d{{4}})?\b|"
    rf"\b\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}}\b|"
    rf"\b\d{{4}}-\d{{2}}-\d{{2}}\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ControlItem:
    path: str
    course: str
    title: str
    kind: str
    due_at: datetime | None
    updated_at: str
    source_provider: str = "blackboard_ultra"
    source_instance: str = "default"
    is_container: bool = False
    date_mentions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ControlResult:
    baseline_created: bool
    pending: tuple[ControlItem, ...]
    new_publications: tuple[ControlItem, ...]
    report_path: Path
    calendar_path: Path


def _read_note(path: Path, target: Path, source: SourceConfig) -> tuple[ControlItem, str] | None:
    if path.name.lower().endswith((".pdf.md", ".docx.md")):
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---\n"):
        return None
    boundary = text.find("\n---\n", 4)
    if boundary < 0:
        return None
    metadata: dict[str, str] = {}
    for line in text[4:boundary].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')
    if metadata.get("source_provider"):
        if metadata.get("source_provider") != source.provider:
            return None
    elif source.provider != "blackboard_ultra" or metadata.get("source") != "Blackboard Ultra":
        return None
    title_match = re.search(r"^#\s+(.+?)\s*$", text[boundary + 5 :], re.MULTILINE)
    title = title_match.group(1) if title_match else path.stem
    title = _normalize_activity_title(title)
    body = text[boundary + 5 :]
    due_at = _parse_datetime(metadata.get("due_at", ""))
    item = ControlItem(
        path=path.relative_to(target).as_posix(),
        course=path.relative_to(target / source.root).parts[0],
        title=title,
        kind=metadata.get("kind", "content"),
        due_at=due_at,
        updated_at=metadata.get("updated_at", ""),
        source_provider=source.provider,
        source_instance=metadata.get("source_instance", source.instance),
        is_container=path.name.lower() == "index.md" and any(child.is_dir() for child in path.parent.iterdir()),
        date_mentions=_extract_date_mentions(body) if metadata.get("kind") == "announcement" else (),
    )
    return item, sha256(text.encode("utf-8")).hexdigest()


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _extract_date_mentions(text: str) -> tuple[str, ...]:
    seen: set[str] = set()
    mentions: list[str] = []
    for match in _DATE_MENTION_RE.finditer(text):
        value = " ".join(match.group(0).split())
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            mentions.append(value)
    return tuple(mentions)


def _load_state(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) and payload.get("format") == 1 and isinstance(payload.get("notes"), dict) else None


def _load_health(path: Path) -> dict[str, Any]:
    default = {
        "format": _HEALTH_FORMAT,
        "sync_status": "unverified",
        "last_local_refresh": None,
        "last_blackboard_sync": None,
        "source_map_sha256": None,
    }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    if not isinstance(payload, dict) or payload.get("format") != _HEALTH_FORMAT:
        return default
    return {**default, **payload}


def _write_health(target: Path, now: datetime, sync_status: str | None) -> dict[str, Any]:
    path = target / _HEALTH_PATH
    health = _load_health(path)
    if sync_status is not None:
        if sync_status not in {"verified", "unavailable", "unverified"}:
            raise ValueError("sync_status inválido")
        health["sync_status"] = sync_status
    health["last_local_refresh"] = now.isoformat()
    if sync_status == "verified":
        health["last_blackboard_sync"] = now.isoformat()
        source_map = target / ".blackboard-sync" / "source-map.json"
        health["source_map_sha256"] = sha256(source_map.read_bytes()).hexdigest() if source_map.is_file() else None
    health["format"] = _HEALTH_FORMAT
    content = json.dumps(health, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    _write_if_changed(path, content)
    return health


def _health_message(health: dict[str, Any], now: datetime, stale_after: timedelta) -> str:
    status = health.get("sync_status", "unverified")
    if status == "unavailable":
        return "> **Fuente académica no disponible:** se conserva el último estado verificado; la vista local sí está actualizada."
    if status != "verified" or not health.get("last_blackboard_sync"):
        return "> **Fuente académica aún no verificada:** esta vista usa únicamente el estado local disponible."
    last_sync = _parse_datetime(str(health["last_blackboard_sync"]))
    if last_sync is None or now - last_sync >= stale_after:
        return f"> **Fuente académica desactualizada:** última sincronización verificada: {health['last_blackboard_sync']}."
    return f"> **Fuente académica verificada:** última sincronización: {health['last_blackboard_sync']}."


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


def _local_stamp(value: datetime) -> str:
    local = value.astimezone(timezone(timedelta(hours=-6)))
    return local.strftime("%Y%m%dT%H%M%S")


def _ics_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _is_actionable(item: ControlItem) -> bool:
    return not item.is_container and item.title.casefold() != "ultradocumentbody"


def _calendar(pending: tuple[ControlItem, ...], now: datetime) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//UTEC//Blackboard Study Control//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for item in pending:
        assert item.due_at is not None
        uid = sha256(item.path.encode("utf-8")).hexdigest() + "@utec-blackboard"
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART;TZID=America/Guatemala:{_local_stamp(item.due_at)}",
            f"SUMMARY:{_ics_escape(item.title)}",
            f"DESCRIPTION:{_ics_escape('Curso: ' + item.course + chr(10) + 'Origen: ' + item.path)}",
            "BEGIN:VALARM",
            "TRIGGER:-PT24H",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_ics_escape('Mañana vence: ' + item.title)}",
            "END:VALARM",
            "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def _link(item: ControlItem) -> str:
    return f"- [ ] [[{item.path}|{item.title}]] — **{item.course}** ({item.kind})"


def _wiki_item_link(item: ControlItem) -> str:
    return f"[[{item.path}|{item.title}]]"


def _group_date_mentions(mentioned_dates: tuple[tuple[ControlItem, str], ...]) -> tuple[tuple[ControlItem, tuple[str, ...]], ...]:
    grouped: dict[str, tuple[ControlItem, list[str]]] = {}
    for item, mention in mentioned_dates:
        current = grouped.setdefault(item.path, (item, []))
        if mention.casefold() not in {value.casefold() for value in current[1]}:
            current[1].append(mention)
    return tuple((item, tuple(values)) for item, values in grouped.values())


def _report(
    now: datetime,
    days: int,
    pending: tuple[ControlItem, ...],
    publications: tuple[ControlItem, ...],
    mentioned_dates: tuple[tuple[ControlItem, str], ...],
    baseline_created: bool,
) -> str:
    horizon = now + timedelta(days=days)
    lines = [
        "# Control académico semanal",
        "",
        f"> Ventana: {now.date().isoformat()} a {horizon.date().isoformat()} · Generado desde la fuente académica sincronizada.",
        "",
        "## Pendiente durante los próximos 7 días",
        "",
    ]
    if pending:
        for item in pending:
            lines.append(f"- [ ] **{item.due_at.astimezone(timezone(timedelta(hours=-6))).strftime('%Y-%m-%d %H:%M')}** · {_wiki_item_link(item)} — **{item.course}** ({item.kind})")
    else:
        lines.append("> La fuente académica no expone fechas de entrega dentro de esta ventana. No se inventaron eventos de calendario.")
    lines.extend(["", "## Fechas mencionadas, pendientes de confirmación", ""])
    if mentioned_dates:
        for item, mentions in _group_date_mentions(mentioned_dates):
            lines.append(f"- [ ] **{' · '.join(mentions)}** · {_wiki_item_link(item)} — **{item.course}**")
        lines.append("")
        lines.append("> Estas fechas aparecen en el texto publicado. No se añadieron al calendario automáticamente.")
    else:
        lines.append("> No se detectaron fechas textuales que requieran confirmación manual.")
    lines.extend(["", "## Nuevas publicaciones desde el último control", ""])
    if baseline_created:
        lines.append("> Línea base creada. Las publicaciones ya existentes no se marcan como nuevas para evitar una alerta histórica masiva.")
    elif publications:
        lines.extend(_link(item) for item in publications)
    else:
        lines.append("> No se detectaron publicaciones nuevas o modificadas desde el último control.")
    lines.extend([
        "",
        "## Enfoque sostenible",
        "",
        "1. Elige una sola entrega o tema de esta lista.",
        "2. Haz una sesión de comprensión de 25 minutos usando `Comprensión/Guía para estudiar con Hermes.md`.",
        "3. Registra una explicación de memoria, un ejercicio y una duda en `Comprensión/Mi registro de comprensión.md`.",
        "4. Agenda el siguiente repaso únicamente después de poder explicarlo sin mirar apuntes.",
        "",
    ])
    return "\n".join(lines)


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _domain_matrix(target: Path) -> str:
    rows: list[tuple[str, str, str, str, str, str, str, str]] = []
    projects = target / "Proyectos de Estudio"
    if projects.exists():
        for journal in sorted(projects.glob("* - Parcial */Bitácora de dominio.md")):
            text = journal.read_text(encoding="utf-8", errors="replace")
            course = journal.parent.name.split(" - ", 1)[0]
            headers: list[str] | None = None
            for line in text.splitlines():
                if not line.strip().startswith("|"):
                    continue
                cells = _split_table_row(line)
                if not cells or all(set(cell) <= {"-", ":", " "} for cell in cells):
                    continue
                normalized = [cell.casefold() for cell in cells]
                if "bloque" in normalized:
                    headers = normalized
                    continue
                if headers is None or len(cells) < len(headers) or "bloque" not in headers:
                    continue
                values = dict(zip(headers, cells))
                block = values.get("bloque", "").strip()
                if not block:
                    continue
                rows.append((
                    course,
                    block,
                    values.get("explicación sin apuntes (0–3)", "").strip(),
                    values.get("aplicación (0–3)", "").strip(),
                    values.get("error/duda concreta", "").strip(),
                    values.get("próxima acción", "").strip(),
                    values.get("próximo repaso", "").strip(),
                    f"[[../{journal.relative_to(target).as_posix()}|Bitácora]]",
                ))
    lines = [
        "# Matriz global de dominio",
        "",
        "> Vista agregada de las bitácoras por materia. Esta nota es generada; las bitácoras originales siguen siendo la fuente de edición.",
        "",
        "| Curso | Bloque | Explicación | Aplicación | Duda o error | Próxima acción | Próximo repaso | Fuente |",
        "|---|---|---:|---:|---|---|---|---|",
    ]
    if rows:
        for course, block, explanation, application, doubt, next_action, next_review, source in sorted(rows):
            explanation = f"{explanation}/3" if explanation else "—"
            application = f"{application}/3" if application else "—"
            cells = [course, block, explanation, application, doubt or "—", next_action or "—", next_review or "—", source]
            lines.append("| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |")
    else:
        lines.append("| — | Aún no hay registros en las bitácoras de dominio. | — | — | — | — | — |")
    lines.extend([
        "",
        "## Regla de lectura",
        "",
        "- `0–1/3`: prioridad de recuperación.",
        "- `2/3`: comprensión parcial; requiere aplicación o corrección.",
        "- `3/3`: revisar que también exista una duda, límite o condición registrada.",
        "",
    ])
    return "\n".join(lines)


def _weak_domain_rows(matrix_content: str) -> tuple[tuple[str, str, str, str, str], ...]:
    weak: list[tuple[str, str, str, str, str]] = []
    for line in matrix_content.splitlines():
        if not line.startswith("|"):
            continue
        cells = _split_table_row(line)
        if len(cells) < 7 or (cells[0] == "Curso" and cells[1] == "Bloque") or cells[0] == "—":
            continue
        explanation = re.match(r"^(\d+)/3$", cells[2])
        application = re.match(r"^(\d+)/3$", cells[3])
        if (explanation and int(explanation.group(1)) <= 1) or (application and int(application.group(1)) <= 1):
            weak.append((cells[0], cells[1], cells[2], cells[3], cells[5]))
    return tuple(sorted(weak, key=lambda row: (row[0], row[1])))


def _review_rows(matrix_content: str, now: datetime) -> tuple[tuple[str, str, str, str], ...]:
    reviews: list[tuple[str, str, str, str]] = []
    for line in matrix_content.splitlines():
        if not line.startswith("|"):
            continue
        cells = _split_table_row(line)
        if len(cells) < 8 or (cells[0] == "Curso" and cells[1] == "Bloque") or cells[0] == "—":
            continue
        review = cells[6]
        parsed = _parse_datetime(review) or _parse_datetime(review + "T23:59:59Z" if re.fullmatch(r"\d{4}-\d{2}-\d{2}", review) else "")
        if parsed is not None and parsed.date() <= (now + timedelta(days=7)).date():
            reviews.append((cells[0], cells[1], review, cells[5]))
    return tuple(sorted(reviews, key=lambda row: (row[2], row[0], row[1])))


def _dashboard(
    now: datetime,
    pending: tuple[ControlItem, ...],
    mentioned_dates: tuple[tuple[ControlItem, str], ...],
    publications: tuple[ControlItem, ...],
    health: dict[str, Any],
    stale_after: timedelta,
    weak_domain: tuple[tuple[str, str, str, str, str], ...],
    review_rows: tuple[tuple[str, str, str, str], ...],
    result_actions: tuple[str, ...] = (),
) -> str:
    attention: list[str] = []
    seen: set[str] = set()
    for item in pending:
        if item.path in seen:
            continue
        seen.add(item.path)
        due = item.due_at.astimezone(timezone(timedelta(hours=-6))).strftime("%Y-%m-%d %H:%M") if item.due_at else ""
        attention.append(f"- [ ] **{due}** · [{item.title}](../{item.path}) — {item.course}")
    for item, mention in mentioned_dates:
        if item.path in seen:
            continue
        seen.add(item.path)
        attention.append(f"- [ ] **Confirmar {mention}** · [{item.title}](../{item.path}) — {item.course}")
    for item in publications:
        if item.path in seen:
            continue
        seen.add(item.path)
        attention.append(f"- [ ] **Nueva publicación** · [{item.title}](../{item.path}) — {item.course}")
    attention.extend(result_actions)
    seen_courses = {item.course for item in pending} | {item.course for item, _mention in mentioned_dates} | {item.course for item in publications}
    for course, block, review, next_action in review_rows:
        if course in seen_courses:
            continue
        seen_courses.add(course)
        action = next_action if next_action not in {"", "—"} else "Hacer recuperación y aplicación"
        attention.append(f"- [ ] **{course} — repaso** · {block} ({review}) — {action}")
    for course, block, explanation, application, next_action in weak_domain:
        if course in seen_courses:
            continue
        seen_courses.add(course)
        action = next_action if next_action not in {"", "—"} else "Practicar una aplicación nueva"
        attention.append(f"- [ ] **{course} — dominio débil** · {block} ({explanation}, {application}) — {action}")
    attention = attention[:8]
    lines = [
        "# Dashboard académico",
        "",
        f"> Última actualización local: {now.astimezone(timezone(timedelta(hours=-6))).strftime('%Y-%m-%d %H:%M')}",
        _health_message(health, now, stale_after),
        "> La sincronización de la fuente académica y la actualización local son procesos separados.",
        "",
        "## Atención ahora",
        "",
    ]
    lines.extend(attention or ["> No hay acciones nuevas priorizadas."])
    lines.extend([
        "",
        "## Vistas de control",
        "",
        "- [[Estado semanal|Estado semanal: cambios, entregas y fechas por confirmar]]",
        "- [[Matriz de dominio|Matriz de dominio por curso]]",
        "- [[Reporte de trazabilidad|Trazabilidad de apuntes y fuentes]]",
        "- [[Reporte de resultados académicos|Resultados, razones y accionables]]",
        "- [[Comparación de diagnósticos|Comparación de intentos y aplicación]]",
        "- [[Checkpoint - Parcial 1/00 - Panel del corte|Checkpoint de parciales]]",
        "- [[Comprensión/Mi registro de comprensión|Registro de comprensión]]",
        "",
        "## Flujo recomendado",
        "",
        "1. Atiende una sola acción de esta portada.",
        "2. Registra la evidencia en la bitácora o el registro de comprensión.",
        "3. Ejecuta `Actualizar-Dashboard-Local.bat` para refrescar esta vista sin abrir la fuente externa.",
        "",
    ])
    return "\n".join(lines)


def _create_learning_files(control_root: Path) -> None:
    learning = control_root / "Comprensión"
    learning.mkdir(parents=True, exist_ok=True)
    guide = learning / "Guía para estudiar con Hermes.md"
    journal = learning / "Mi registro de comprensión.md"
    if not guide.exists():
        _write_if_changed(guide, """# Guía para estudiar con Hermes

## Sesión mínima de 25 minutos

1. Abre **una** nota de la fuente académica o un sidecar PDF/DOCX relacionado.
2. Pídele a Hermes: `Ayúdame a comprender este tema paso a paso. Primero hazme 3 preguntas de diagnóstico; no me des la solución antes de que intente responder.`
3. Escribe una explicación corta de memoria y resuelve un ejemplo pequeño.
4. Registra la duda que no pudiste resolver y programa el próximo repaso.

## Regla de carga sostenible

Con trabajo y materias simultáneas, prioriza una sesión completa de comprensión sobre acumular listas largas. Un tema cuenta como trabajado solo cuando puedes explicarlo, aplicarlo en un ejemplo y nombrar una duda o límite.
""")
    if not journal.exists():
        _write_if_changed(journal, """# Mi registro de comprensión

| Fecha | Curso | Tema / enlace | Lo explico sin mirar | Ejercicio aplicado | Duda concreta | Próximo repaso |
|---|---|---|---|---|---|---|
| | | | Sí / Aún no | | | |
""")


def refresh_control(
    target: Path,
    *,
    now: datetime | None = None,
    days: int = 7,
    sync_status: str | None = None,
    stale_after_hours: int = 48,
) -> ControlResult:
    target = Path(target)
    if days <= 0:
        raise ValueError("days debe ser positivo")
    if stale_after_hours <= 0:
        raise ValueError("stale_after_hours debe ser positivo")
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    notes: dict[str, tuple[ControlItem, str]] = {}
    for source in load_source_configs(target):
        source_root = target / source.root
        for path in sorted(source_root.rglob("*.md")):
            parsed = _read_note(path, target, source)
            if parsed is not None:
                notes[parsed[0].path] = parsed
    state_path = target / _STATE_PATH
    previous = _load_state(state_path)
    baseline_created = previous is None
    previous_notes = {} if previous is None else previous["notes"]
    publications = () if baseline_created else tuple(
        item for path, (item, digest) in sorted(notes.items()) if previous_notes.get(path) != digest and _is_actionable(item)
    )
    horizon = now + timedelta(days=days)
    pending = tuple(sorted(
        (item for item, _digest in notes.values() if _is_actionable(item) and item.due_at is not None and now <= item.due_at < horizon),
        key=lambda item: (item.due_at or now, item.course, item.title, item.path),
    ))
    mentioned_dates = tuple(
        (item, mention)
        for item, _digest in sorted(notes.values(), key=lambda pair: (pair[0].course, pair[0].title, pair[0].path))
        if _is_actionable(item)
        for mention in item.date_mentions
    )
    state_content = json.dumps({"format": 1, "notes": {path: digest for path, (_item, digest) in sorted(notes.items())}}, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    _write_if_changed(state_path, state_content)
    health = _write_health(target, now, sync_status)
    control_root = target / _CONTROL_DIRECTORY
    _create_learning_files(control_root)
    report_path = control_root / "Estado semanal.md"
    calendar_path = control_root / "UTEC-Fechas.ics"
    matrix_content = _domain_matrix(target)
    _write_if_changed(report_path, _report(now, days, pending, publications, mentioned_dates, baseline_created))
    _write_if_changed(calendar_path, _calendar(pending, now))
    _write_if_changed(control_root / "Matriz de dominio.md", matrix_content)
    _write_if_changed(control_root / "Reporte de trazabilidad.md", build_traceability_report(target))
    write_results_report(target)
    _write_if_changed(control_root / "Comparación de diagnósticos.md", build_diagnostic_comparison(target))
    _write_if_changed(control_root / "00 - Dashboard académico.md", _dashboard(now, pending, mentioned_dates, publications, health, timedelta(hours=stale_after_hours), _weak_domain_rows(matrix_content), _review_rows(matrix_content, now), result_attention_lines(target)))
    _write_if_changed(control_root / "Recordatorios.md", "# Recordatorios\n\n" + ("\n".join(_link(item) for item in pending) if pending else "> Sin recordatorios publicados para los próximos 7 días.\n"))
    return ControlResult(baseline_created, pending, publications, report_path, calendar_path)
