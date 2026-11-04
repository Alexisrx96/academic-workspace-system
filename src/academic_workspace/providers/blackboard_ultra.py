from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from ..models import Snapshot
from .contracts import (
    SourceCapabilities,
    SourceCourse,
    SourceHealth,
    SourceIdentity,
    SourceItem,
    SourceSnapshot,
    parse_datetime,
)


class BlackboardUltraProvider:
    provider_id = "blackboard_ultra"

    def __init__(self, collector: Callable[[], Snapshot], *, instance: str = "default") -> None:
        self.collector = collector
        self.instance_id = instance
        self._last_error: str | None = None

    def collect_legacy_snapshot(self) -> Snapshot:
        try:
            snapshot = self.collector()
        except Exception as error:
            self._last_error = str(error)
            raise
        self._last_error = None
        return snapshot

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

    def collect_snapshot(self) -> SourceSnapshot:
        legacy = self.collect_legacy_snapshot()
        courses = tuple(
            SourceCourse(
                identity=SourceIdentity(self.provider_id, self.instance_id, course.id),
                code=course.course_id,
                name=course.name,
                metadata={"description": course.description, "availability": course.availability},
            )
            for course in legacy.courses
        )
        course_ids = {course.identity.external_id: course for course in courses}
        items = tuple(
            SourceItem(
                identity=SourceIdentity(self.provider_id, self.instance_id, activity.id),
                course=course_ids[activity.course_id].identity,
                kind=activity.kind,
                title=activity.title,
                body=activity.body,
                due_at=parse_datetime(activity.due_at),
                created_at=parse_datetime(activity.created_at),
                updated_at=parse_datetime(activity.updated_at),
                attachments=activity.attachments,
                metadata={"url": activity.url, "is_container": activity.is_container, "content_path": activity.content_path},
            )
            for activity in legacy.activities
            if activity.course_id in course_ids
        )
        return SourceSnapshot(self.provider_id, self.instance_id, courses, items)

    def health(self) -> SourceHealth:
        checked = datetime.now(timezone.utc).isoformat()
        if self._last_error:
            return SourceHealth("unavailable", checked, self._last_error)
        return SourceHealth("unknown", checked, "Aún no se ha recolectado un snapshot")
