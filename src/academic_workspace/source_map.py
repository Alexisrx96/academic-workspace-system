from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from .models import Activity, Course, Snapshot, canonical_json
from .render import _activity_directory, _attachment_filename, _course_key, _safe_name


@dataclass(frozen=True, slots=True)
class SourceMap:
    payload: dict[str, Any]
    content: str

    @property
    def snapshot_sha256(self) -> str:
        return str(self.payload["snapshot_sha256"])


def _digest(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _course_entry(course: Course, *, source_root: str = "Blackboard", source_provider: str = "blackboard_ultra", source_instance: str = "default") -> dict[str, Any]:
    entry = {
        "id": course.id,
        "course_code": course.course_id,
        "source_provider": source_provider,
        "source_instance": source_instance,
        "path": f"{source_root.strip('/')}/{_course_key(course)}",
        "fingerprint": _digest(course),
    }
    return entry


def _item_entry(
    course: Course,
    activity: Activity,
    *,
    source_root: str = "Blackboard",
    source_provider: str = "blackboard_ultra",
    source_instance: str = "default",
) -> dict[str, Any]:
    note_name = "index.md" if activity.is_container else f"{_safe_name(activity.title)}--{_safe_name(activity.id)}.md"
    directory = _activity_directory(course, activity, source_root=source_root)
    attachments = []
    for raw in sorted(activity.attachments, key=lambda item: (str(item.get("id", "")), str(item.get("name", "")))):
        attachment = dict(raw)
        filename = _attachment_filename(attachment)
        attachments.append({
            "id": str(attachment.get("id") or ""),
            "name": str(attachment.get("name") or ""),
            "mime_type": attachment.get("mime_type"),
            "size": attachment.get("size"),
            "path": f"{directory}/Adjuntos/{filename}",
        })
    return {
        "source_provider": source_provider,
        "source_instance": source_instance,
        "id": activity.id,
        "course_id": activity.course_id,
        "kind": activity.kind,
        "is_container": activity.is_container,
        "content_path": list(activity.content_path),
        "note_path": f"{directory}/{note_name}",
        "attachments": attachments,
        "fingerprint": _digest(activity),
    }


def build_source_map(
    snapshot: Snapshot,
    *,
    source_root: str = "Blackboard",
    source_provider: str = "blackboard_ultra",
    source_instance: str = "default",
) -> SourceMap:
    courses = {course.id: course for course in snapshot.courses}
    payload = {
        "format": 2,
        "output_format": 2,
        "snapshot_sha256": _digest(snapshot),
        "source_provider": source_provider,
        "source_instance": source_instance,
        "source_root": source_root.strip("/"),
        "courses": [
            _course_entry(course, source_root=source_root, source_provider=source_provider, source_instance=source_instance)
            for course in snapshot.courses
        ],
        "items": [
            _item_entry(
                courses[activity.course_id],
                activity,
                source_root=source_root,
                source_provider=source_provider,
                source_instance=source_instance,
            )
            for activity in snapshot.activities
            if activity.course_id in courses
        ],
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return SourceMap(payload=payload, content=content)


def _entries(value: SourceMap) -> dict[str, str]:
    entries = {
        f"course:{course['id']}": str(course["fingerprint"])
        for course in value.payload["courses"]
    }
    entries.update({
        f"item:{item['course_id']}:{item['id']}": str(item["fingerprint"])
        for item in value.payload["items"]
    })
    return entries


def diff_source_maps(current: SourceMap, previous: SourceMap | None) -> dict[str, int]:
    before = _entries(previous) if previous is not None else {}
    after = _entries(current)
    return {
        "added": len(after.keys() - before.keys()),
        "changed": sum(before[key] != after[key] for key in after.keys() & before.keys()),
        "removed": len(before.keys() - after.keys()),
    }
