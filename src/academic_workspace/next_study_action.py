from __future__ import annotations

from typing import Any


def next_study_action(result: str, error_tags: tuple[str, ...], confidence: int | None) -> dict[str, Any]:
    if result in {"calculation_mismatch", "unit_mismatch", "formalization_uncertain"}:
        tags = ", ".join(error_tags) if error_tags else "el error observado"
        return {"schema": "study-next-action.v1", "action": "targeted_practice", "reason": f"Corregir {tags} con un caso análogo.", "error_tags": list(error_tags)}
    if result in {"verified", "externally_confirmed"} and (confidence is None or confidence <= 1):
        return {"schema": "study-next-action.v1", "action": "retrieval_recheck", "reason": "Verificar retención con recuperación sin ayuda.", "error_tags": list(error_tags)}
    if error_tags:
        return {"schema": "study-next-action.v1", "action": "adversarial_check", "reason": "Contrastar el concepto con un caso límite.", "error_tags": list(error_tags)}
    return {"schema": "study-next-action.v1", "action": "schedule_review", "reason": "Programar revisión espaciada.", "error_tags": []}
