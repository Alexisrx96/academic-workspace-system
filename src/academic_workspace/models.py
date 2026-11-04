from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping


def _text(value: Any) -> str | None:
    return None if value is None else str(value)


def _normalize_activity_title(title: str) -> str:
    match = re.search(r"Adjuntos/([^\]|]+)", title)
    if not match:
        return title
    filename = Path(match.group(1)).name
    filename = re.sub(r"--_[^/]+(?=\.[^.]+$)", "", filename)
    return filename


@dataclass(frozen=True, slots=True)
class Course:
    id: str
    name: str
    course_id: str | None = None
    description: str | None = None
    availability: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Course":
        return cls(
            id=str(value["id"]),
            name=str(value.get("name") or value["id"]),
            course_id=_text(value.get("course_id")),
            description=_text(value.get("description")),
            availability=_text(value.get("availability")),
        )


@dataclass(frozen=True, slots=True)
class Activity:
    id: str
    course_id: str
    title: str
    kind: str
    body: str | None = None
    due_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    url: str | None = None
    is_container: bool = False
    content_path: tuple[str, ...] = field(default_factory=tuple)
    attachments: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Activity":
        content_path = tuple(str(part) for part in (value.get("content_path") or ()))
        title = _normalize_activity_title(str(value.get("title") or value["id"]))
        if title.casefold() == "ultradocumentbody" and content_path:
            parent = content_path[-1]
            title = parent.rsplit("--", 1)[0] if "--" in parent else parent
        return cls(
            id=str(value["id"]),
            course_id=str(value["course_id"]),
            title=title,
            kind=str(value.get("kind") or "content"),
            body=_text(value.get("body")),
            due_at=_text(value.get("due_at")),
            created_at=_text(value.get("created_at")),
            updated_at=_text(value.get("updated_at")),
            url=_text(value.get("url")),
            is_container=bool(value.get("is_container")),
            content_path=content_path,
            attachments=tuple(
                sorted(
                    (dict(item) for item in (value.get("attachments") or ())),
                    key=lambda item: (str(item.get("id", "")), str(item.get("name", ""))),
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class Snapshot:
    courses: tuple[Course, ...]
    activities: tuple[Activity, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Snapshot":
        return cls(
            courses=tuple(sorted((Course.from_mapping(x) for x in value.get("courses", ())), key=lambda x: x.id)),
            activities=tuple(sorted((Activity.from_mapping(x) for x in value.get("activities", ())), key=lambda x: (x.course_id, x.kind, x.id))),
        )


def _canonical_value(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(item) for key, item in value.items() if key != "source_url"}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(_canonical_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
