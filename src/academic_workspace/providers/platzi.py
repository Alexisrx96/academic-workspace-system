from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .contracts import SourceCapabilities, SourceCourse, SourceHealth, SourceIdentity, SourceItem, SourceSnapshot, parse_datetime


class PlatziProvider:
    """Local Platzi adapter; consumes an authorized export, never scrapes credentials."""

    provider_id = "platzi"

    def __init__(self, path: Path, *, instance: str = "default") -> None:
        self.path = Path(path)
        self.instance_id = instance

    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(courses=True, content=True, assignments=True, due_dates=True, attachments=True)

    def _load(self) -> dict[str, Any]:
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("el export de Platzi debe ser un objeto JSON")
        return value

    def collect_snapshot(self) -> SourceSnapshot:
        payload = self._load()
        courses = []
        items = []
        for raw_course in sorted(payload.get("courses", ()), key=lambda item: str(item.get("id", ""))):
            course_id = str(raw_course["id"])
            identity = SourceIdentity(self.provider_id, self.instance_id, course_id)
            course_metadata = {key: value for key, value in dict(raw_course).items() if key not in {"lessons", "projects"}}
            courses.append(SourceCourse(identity, raw_course.get("code"), str(raw_course.get("name") or course_id), course_metadata))
            module_items = []
            for module in raw_course.get("modules", ()):
                module_id = str(module.get("id", ""))
                for raw_item in tuple(module.get("lessons", ())) + tuple(module.get("projects", ())):
                    enriched = dict(raw_item)
                    enriched.setdefault("metadata", {}).update({"module_id": module_id, "module_title": module.get("title", module_id)})
                    module_items.append(enriched)
            course_items = tuple(raw_course.get("lessons", ())) + tuple(raw_course.get("projects", ())) + tuple(module_items)
            projects = {str(item.get("id")) for item in tuple(raw_course.get("projects", ())) + tuple(item for module in raw_course.get("modules", ()) for item in module.get("projects", ()))}
            for raw_item in sorted(course_items, key=lambda item: str(item.get("id", ""))):
                item_id = str(raw_item["id"])
                kind = "assignment" if item_id in projects else "content"
                metadata = dict(raw_item.get("metadata") or {})
                metadata.update({key: raw_item[key] for key in ("completed", "progress", "url") if key in raw_item})
                items.append(SourceItem(
                    identity=SourceIdentity(self.provider_id, self.instance_id, f"{course_id}:{item_id}"),
                    course=identity,
                    kind=kind,
                    title=str(raw_item.get("title") or item_id),
                    body=raw_item.get("body") or raw_item.get("description"),
                    due_at=parse_datetime(raw_item.get("due_at")),
                    created_at=parse_datetime(raw_item.get("created_at")),
                    updated_at=parse_datetime(raw_item.get("updated_at")),
                    attachments=tuple(raw_item.get("attachments") or ()),
                    metadata=metadata,
                ))
        return SourceSnapshot(self.provider_id, self.instance_id, tuple(courses), tuple(items))

    def health(self) -> SourceHealth:
        checked = datetime.now(timezone.utc).isoformat()
        try:
            self._load()
        except (OSError, json.JSONDecodeError, ValueError) as error:
            return SourceHealth("unavailable", checked, str(error))
        return SourceHealth("verified", checked, "snapshot local de Platzi")
