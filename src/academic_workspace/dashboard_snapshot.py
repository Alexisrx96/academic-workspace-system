from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _attention(target: Path) -> list[dict[str, str]]:
    path = target / "Control Académico" / "00 - Dashboard académico.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        section = text.split("## Atención ahora\n", 1)[1].split("\n## ", 1)[0]
    except IndexError:
        return []
    result = []
    for line in section.splitlines():
        if not line.startswith("- [ ] "):
            continue
        link = re.search(r"\]\(\.\./(.+?)\)", line)
        course = line.rsplit(" — ", 1)[-1].strip() if " — " in line else ""
        result.append({
            "text": line[6:].strip(),
            "course": course,
            "source": link.group(1) if link else "",
        })
    return result


def _domain(target: Path) -> list[dict[str, str]]:
    path = target / "Control Académico" / "Matriz de dominio.md"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    result = []
    for line in lines:
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 7 or (cells[0] == "Curso" and cells[1] == "Bloque") or cells[0] == "—" or set(cells[0]) <= {"-", ":", " "}:
            continue
        result.append({
            "course": cells[0],
            "block": cells[1],
            "explanation": cells[2],
            "application": cells[3],
            "doubt": cells[4],
            "next_action": cells[5],
        })
    return sorted(result, key=lambda row: (row["course"], row["block"]))


def build_snapshot(target: Path) -> dict[str, Any]:
    target = Path(target)
    health = _load_json(target / ".blackboard-sync" / "sync-health.json")
    return {
        "format": 1,
        "health": {
            "sync_status": health.get("sync_status", "unverified"),
            "last_blackboard_sync": health.get("last_blackboard_sync"),
            "last_local_refresh": None,
        },
        "attention": _attention(target),
        "domain": _domain(target),
        "views": {
            "dashboard": "Control Académico/00 - Dashboard académico.md",
            "weekly": "Control Académico/Estado semanal.md",
            "domain": "Control Académico/Matriz de dominio.md",
            "results": "Control Académico/Reporte de resultados académicos.md",
        },
    }
