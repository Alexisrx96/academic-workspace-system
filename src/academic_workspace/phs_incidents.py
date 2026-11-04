from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any


def _classification(validation: dict[str, Any]) -> str:
    return {
        "unit_mismatch": "unit_error",
        "calculation_mismatch": "formalization_error",
        "formalization_uncertain": "formalization_error",
        "phs_unavailable": "configuration",
        "script_failed": "unknown",
    }.get(str(validation.get("status")), "unknown")


def build_phs_incident(course: str, topic: str, validation: dict[str, Any], checks: dict[str, bool]) -> dict[str, Any]:
    required = {
        "reproducible", "minimal_case", "input_verified", "formalization_verified",
        "units_verified", "independent_calculation", "similar_examples_checked",
        "environment_recorded", "phs_version_recorded", "alternative_explanations_excluded",
    }
    complete = required.issubset(checks) and all(checks[key] for key in required)
    classification = _classification(validation)
    if complete and validation.get("status") == "script_failed":
        classification = "phs_engine"
    identity = {"course": course, "topic": topic, "validation": validation, "checks": checks}
    incident_id = "phs-incident:" + sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "schema": "phs-incident.v1",
        "incident_id": incident_id,
        "course": course,
        "topic": topic,
        "classification": classification,
        "status": "open",
        "validation": validation,
        "checks": checks,
        "escalation_status": "ready_for_phs_issue" if classification == "phs_engine" and complete else "needs_more_investigation",
    }




def prepare_phs_issue(report: dict[str, Any]) -> dict[str, Any]:
    if report.get("escalation_status") != "ready_for_phs_issue":
        raise ValueError("el incidente aún no supera el gate de investigación")
    validation = report.get("validation", {})
    body = (
        "## Bug Description\n\n"
        f"PHS produce un fallo reproducible en el caso de {report.get('topic')}.\n\n"
        "## Minimal Reproduction\n\n"
        f"Script: `{validation.get('script_path', '<missing>')}`\n\n"
        "## Expected Behavior\n\nEl caso debería ejecutarse según la formalización verificada.\n\n"
        "## Actual Behavior\n\n"
        f"{validation.get('error', validation.get('stderr', '<see validation report>'))}\n\n"
        "## Environment\n\n"
        f"PHS version: {validation.get('phs_version', '<record required>')}\n"
    )
    return {
        "schema": "phs-issue-draft.v1",
        "incident_id": report["incident_id"],
        "title": f"PHS: reproducible failure in {report.get('topic')}",
        "body": body,
        "requires_user_approval": True,
        "published": False,
    }


def write_phs_incident(target: Path, report: dict[str, Any]) -> dict[str, Path]:
    target = Path(target)
    course = str(report["course"])
    slug = report["incident_id"].split(":", 1)[-1][:16]
    directory = target / "02 - Cursos" / course / "Cálculos" / "reportes"
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / f"phs-incident-{slug}.json"
    markdown_path = directory / f"phs-incident-{slug}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    checks = "\n".join(f"- `{key}`: {'sí' if value else 'no'}" for key, value in sorted(report.get("checks", {}).items()))
    validation = report.get("validation", {})
    markdown = f"# Incidente PHS: {report['topic']}\n\n"
    markdown += f"- Estado: **{report['status']}**\n- Clasificación: **{report['classification']}**\n- Escalamiento: **{report['escalation_status']}**\n\n"
    markdown += "## Validación\n\n```json\n" + json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True) + "\n```\n\n"
    markdown += "## Gate de investigación\n\n" + checks + "\n"
    markdown_path.write_text(markdown, encoding="utf-8", newline="\n")
    return {"json": json_path, "markdown": markdown_path}
