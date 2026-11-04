from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    provider: str
    instance: str
    external_id: str

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.instance}:{self.external_id}"


@dataclass(frozen=True, slots=True)
class SourceCapabilities:
    courses: bool = False
    announcements: bool = False
    content: bool = False
    assignments: bool = False
    due_dates: bool = False
    attachments: bool = False
    feedback: bool = False
    grades: bool = False


@dataclass(frozen=True, slots=True)
class SourceHealth:
    status: str
    checked_at: str
    message: str | None = None


@dataclass(frozen=True, slots=True)
class SourceCourse:
    identity: SourceIdentity
    code: str | None
    name: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SourceItem:
    identity: SourceIdentity
    course: SourceIdentity
    kind: str
    title: str
    body: str | None = None
    due_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    attachments: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    provider: str
    instance: str
    courses: tuple[SourceCourse, ...]
    items: tuple[SourceItem, ...]


class AcademicSourceProvider(Protocol):
    provider_id: str
    instance_id: str

    def capabilities(self) -> SourceCapabilities:
        ...

    def collect_snapshot(self) -> SourceSnapshot:
        ...

    def health(self) -> SourceHealth:
        ...


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
