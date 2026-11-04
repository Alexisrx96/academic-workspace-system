from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .contracts import (
    SourceCapabilities,
    SourceCourse,
    SourceHealth,
    SourceIdentity,
    SourceItem,
    SourceSnapshot,
    parse_datetime,
)


class FixtureProvider:
    provider_id = "fixture"

    def __init__(self, path: Path, *, instance: str = "default") -> None:
        self.path = Path(path)
        self.instance_id = instance

    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            courses=True,
            announcements=True,
            content=True,
            assignments=True,
            due_dates=True,
            attachments=True,
            feedback=True,
        )

    def _load(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def collect_snapshot(self) -> SourceSnapshot:
        payload = self._load()
        courses = tuple(
            SourceCourse(
                identity=SourceIdentity(self.provider_id, self.instance_id, str(course["id"])),
                code=str(course["code"]) if course.get("code") is not None else None,
                name=str(course.get("name") or course["id"]),
                metadata=dict(course.get("metadata") or {}),
            )
            for course in sorted(payload.get("courses", ()), key=lambda item: str(item["id"]))
        )
        course_ids = {course.identity.external_id: course.identity for course in courses}
        items = []
        for item in sorted(payload.get("items", ()), key=lambda value: (str(value.get("course_id", "")), str(value["id"]))):
            course = course_ids[str(item["course_id"])]
            items.append(SourceItem(
                identity=SourceIdentity(self.provider_id, self.instance_id, str(item["id"])),
                course=course,
                kind=str(item.get("kind") or "content"),
                title=str(item.get("title") or item["id"]),
                body=item.get("body"),
                due_at=parse_datetime(item.get("due_at")),
                created_at=parse_datetime(item.get("created_at")),
                updated_at=parse_datetime(item.get("updated_at")),
                attachments=tuple(item.get("attachments") or ()),
                metadata=dict(item.get("metadata") or {}),
            ))
        return SourceSnapshot(self.provider_id, self.instance_id, courses, tuple(items))

    def health(self) -> SourceHealth:
        checked = datetime.now(timezone.utc).isoformat()
        try:
            self._load()
        except (OSError, json.JSONDecodeError) as error:
            return SourceHealth("unavailable", checked, str(error))
        return SourceHealth("verified", checked)
