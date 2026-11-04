from __future__ import annotations

from typing import Any

_POLICY = {
    "read_official_source": (False, False),
    "search_web": (True, False),
    "fetch_external_source": (True, False),
    "transform_notes_to_phs": (True, False),
    "write_generated_phs": (True, False),
    "execute_phs": (True, False),
    "modify_user_note": (True, False),
    "prepare_issue_draft": (False, False),
    "create_incident_report": (False, False),
    "publish_issue": (True, True),
    "publish_external_content": (True, True),
}


def permission_for(action: str, *, scope: str = "", destination: str = "") -> dict[str, Any]:
    if action not in _POLICY:
        raise ValueError(f"permiso desconocido: {action}")
    requires_confirmation, external_side_effect = _POLICY[action]
    return {
        "schema": "study-permission.v1",
        "action": action,
        "scope": scope,
        "destination": destination,
        "reversible": not external_side_effect,
        "requires_confirmation": requires_confirmation,
        "external_side_effect": external_side_effect,
    }
