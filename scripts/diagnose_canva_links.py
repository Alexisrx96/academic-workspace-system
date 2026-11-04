from __future__ import annotations

import json
from academic_workspace.live_browser import LiveBrowserTransport

TARGETS = {
    "Aspectos de nueva Visión",
    "Determinación de la Interacción",
    "Aspectos de Interacción e Interdependencia",
    "Introducción Tendencias Administrativas Modernas",
}
QUERY = "%40view=Summary&expand=assignedGroups%2CselfEnrollmentGroups.group%2CgradebookCategory&includeInActivityTracking=true&limit=100&offset=0"


def walk(transport, parent: str, seen: set[str]):
    if parent in seen:
        return
    seen.add(parent)
    payload = transport.get_json(f"/learn/api/v1/courses/_8208_1/contents/{parent}/children?{QUERY}")
    for item in payload.get("results", ()):
        title = str(item.get("title") or "")
        if title in TARGETS:
            print(json.dumps({"title": title, "id": item.get("id"), "handler": item.get("contentHandler"), "keys": sorted(item.keys()), "body": item.get("body"), "description": item.get("description"), "contentDetail": item.get("contentDetail"), "url": item.get("url"), "launchUrl": item.get("launchUrl"), "link": item.get("link")}, ensure_ascii=False, indent=2))
        if item.get("contentHandler") in {"resource/x-bb-folder", "resource/x-bb-lesson"}:
            walk(transport, str(item["id"]), seen)


with LiveBrowserTransport() as transport:
    walk(transport, "ROOT", set())
