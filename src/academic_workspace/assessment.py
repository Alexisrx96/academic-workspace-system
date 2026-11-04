from __future__ import annotations

from pathlib import Path


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return [], []
    headers: list[str] = []
    rows: list[dict[str, str]] = []
    for line in lines:
        if not line.startswith("|"):
            continue
        cells = _cells(line)
        if not cells or all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        normalized = [cell.casefold() for cell in cells]
        if "bloque" in normalized and not headers:
            headers = normalized
            continue
        if headers and len(cells) >= len(headers):
            rows.append(dict(zip(headers, cells)))
    return headers, rows


def _score(value: str | None) -> str:
    return value.strip() if value and value.strip() else "—"


def _status(initial: str, second: str, evidence: str) -> str:
    if second != "—" and evidence not in {"", "—"}:
        return "aplicado"
    if second != "—":
        return "revisado"
    if initial != "—":
        return "diagnosticado"
    return "sin registrar"


def build_diagnostic_comparison(target: Path) -> str:
    target = Path(target)
    projects = target / "Proyectos de Estudio"
    lines = [
        "# Comparación de diagnósticos",
        "",
        "> Vista generada. Los registros de diagnóstico son editables por el estudiante y nunca se sobrescriben.",
        "",
        "| Curso | Bloque | Diagnóstico inicial | Segundo intento | Evidencia de aplicación | Estado | Fuente |",
        "|---|---|---:|---:|---|---|---|",
    ]
    if not projects.exists():
        lines.append("| — | Aún no hay proyectos de estudio. | — | — | — | sin registrar | — |")
        return "\n".join(lines) + "\n"
    found = False
    for project in sorted(projects.glob("* - Parcial */")):
        registry = project / "Registro de diagnósticos.md"
        bitacora = project / "Bitácora de dominio.md"
        _, records = _rows(registry)
        _, domain_rows = _rows(bitacora)
        blocks = {row.get("bloque", "").strip() for row in domain_rows if row.get("bloque", "").strip()}
        for record in records:
            blocks.add(record.get("bloque", "").strip())
        blocks.discard("")
        course = project.name.split(" - ", 1)[0]
        for block in sorted(blocks):
            attempts = [row for row in records if row.get("bloque", "").strip() == block]
            initial = next((row for row in attempts if row.get("intento", "").strip().casefold() in {"inicial", "1", "diagnóstico inicial"}), None)
            second = next((row for row in attempts if row.get("intento", "").strip().casefold() in {"segundo", "2", "segundo intento"}), None)
            initial_score = _score(initial.get("explicación", "") if initial else "")
            second_score = _score(second.get("explicación", "") if second else "")
            evidence = (second or initial or {}).get("evidencia de aplicación", "—") or "—"
            status = _status(initial_score, second_score, evidence)
            source = f"[[../{registry.relative_to(target).as_posix()}|Registro]]" if registry.exists() else "—"
            lines.append(f"| {course} | {block} | {initial_score} | {second_score} | {evidence} | {status} | {source} |")
            found = True
    if not found:
        lines.append("| — | Aún no hay bloques en las bitácoras. | — | — | — | sin registrar | — |")
    lines.extend([
        "",
        "## Estados",
        "",
        "- `sin registrar`: aún no existe evidencia.",
        "- `diagnosticado`: existe un intento inicial.",
        "- `revisado`: existe un segundo intento sin evidencia de aplicación.",
        "- `aplicado`: existe un segundo intento y evidencia de aplicación.",
        "",
    ])
    return "\n".join(lines) + "\n"
