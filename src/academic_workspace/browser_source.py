from __future__ import annotations

from collections.abc import Mapping
from html import unescape
from html.parser import HTMLParser
import mimetypes
import re
from typing import Any, Protocol
from urllib.parse import urlsplit

from .models import Snapshot


class JsonTransport(Protocol):
    def get_json(self, path: str) -> Mapping[str, Any]: ...


_CHILD_QUERY = "%40view=Summary&expand=assignedGroups%2CselfEnrollmentGroups.group%2CgradebookCategory&includeInActivityTracking=true&limit=100&offset=0"


def _plain(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = value.get("displayText") or value.get("rawText")
    if value in (None, ""):
        return None
    raw = str(value)
    decoded = unescape(raw)
    link_names = re.findall(r'"linkName"\s*:\s*"([^"]+)"', decoded, flags=re.IGNORECASE)
    decoded = re.sub(r'[, ]*"linkName"\s*:\s*"[^"]*"\s*}', " ", decoded, flags=re.IGNORECASE)
    embedded_urls = re.findall(r"(?:src|href)\s*=\s*[\"']([^\"']+)[\"']", decoded, flags=re.IGNORECASE)
    direct_urls = re.findall(r"https?://[^\s<>\"']+", decoded, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", decoded)
    plain = re.sub(r"\s+", " ", text).strip()
    urls = []
    for url in embedded_urls + direct_urls:
        if url not in urls:
            urls.append(url)
    combined = " ".join(part for part in (plain, " ".join(urls), " ".join(link_names)) if part)
    return combined or None


def _next_path(value: Any) -> str | None:
    if not value:
        return None
    parsed = urlsplit(str(value))
    return parsed.path + (("?" + parsed.query) if parsed.query else "")


_BLACKBOARD_HOST = "utecvirtual.blackboard.com"


def _blackboard_file_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    if parsed.netloc and parsed.netloc != _BLACKBOARD_HOST:
        return None
    if not parsed.path.startswith("/bbcswebdav/"):
        return None
    return parsed.path + (("?" + parsed.query) if parsed.query else "")


def _mime_type(name: str) -> str | None:
    return mimetypes.guess_type(name)[0]


class _BlackboardLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            url = _blackboard_file_url(self._href)
            if url:
                name = " ".join("".join(self._text).split()) or "adjunto"
                self.links.append((name, url))
            self._href = None
            self._text = []


def _external_link_url(item: Mapping[str, Any], handler: str) -> str | None:
    detail = item.get("contentDetail") or {}
    payload = detail.get(handler) if isinstance(detail, Mapping) else None
    if isinstance(payload, Mapping) and isinstance(payload.get("url"), str):
        return payload["url"]
    return None


def _attachments(item: Mapping[str, Any], handler: str, item_id: str) -> tuple[dict[str, Any], ...]:
    output: list[dict[str, Any]] = []
    detail = item.get("contentDetail") or {}
    file = (detail.get(handler) or {}).get("file") if isinstance(detail, Mapping) else None
    if isinstance(file, Mapping):
        source_url = _blackboard_file_url(file.get("permanentUrl"))
        filename = str(file.get("fileName") or item.get("title") or "adjunto")
        if source_url:
            output.append({
                "id": item_id,
                "name": filename,
                "mime_type": file.get("mimeType") or _mime_type(filename),
                "size": file.get("fileSize"),
                "source_url": source_url,
            })

    parser = _BlackboardLinkParser()
    parser.feed(str((item.get("body") or {}).get("rawText") or ""))
    known = {str(resource["source_url"]) for resource in output}
    for position, (name, source_url) in enumerate(parser.links, start=1):
        if source_url not in known:
            output.append({
                "id": f"{item_id}-embedded-{position}",
                "name": name,
                "mime_type": _mime_type(name),
                "size": None,
                "source_url": source_url,
            })
            known.add(source_url)
    return tuple(output)


class BrowserApiCollector:
    """Read the internal JSON endpoints observed in UTEC Blackboard Ultra.

    Numeric and letter grades are deliberately excluded. The gradebook feed is
    touched only to preserve textual instructor feedback requested by the user.
    """

    def __init__(self, transport: JsonTransport):
        self.transport = transport

    def _pages(self, path: str):
        while path:
            payload = self.transport.get_json(path)
            yield from payload.get("results", ())
            path = _next_path((payload.get("paging") or {}).get("nextPage"))

    def collect(self) -> Snapshot:
        me = self.transport.get_json("/learn/api/v1/users/me")
        user_id = str(me["id"])
        memberships_path = (
            f"/learn/api/v1/users/{user_id}/memberships?"
            "expand=course.effectiveAvailability,course.permissions,courseRole&includeCount=true&limit=10000"
        )
        memberships = self.transport.get_json(memberships_path).get("results", ())
        courses: list[dict[str, Any]] = []
        activities: list[dict[str, Any]] = []

        for membership in sorted(memberships, key=lambda x: str(x.get("courseId", ""))):
            course = membership.get("course") or {}
            if not course.get("effectiveAvailability", course.get("isAvailable", True)):
                continue
            course_id = str(course["id"])
            courses.append({
                "id": course_id,
                "course_id": course.get("courseId"),
                "name": course.get("name") or course.get("displayName") or course_id,
                "description": _plain(course.get("description")),
                "availability": "available",
            })
            activities.extend(self._announcements(course_id))
            activities.extend(self._contents(course_id))
            activities.extend(self._feedback(course_id, user_id))

        return Snapshot.from_mapping({"courses": courses, "activities": activities})

    def _announcements(self, course_id: str) -> list[dict[str, Any]]:
        path = (
            f"/learn/api/v1/courses/{course_id}/announcements?"
            "limit=100&offset=0&sort=startDateRestriction%28desc%29"
        )
        return [{
            "id": str(item["id"]),
            "course_id": course_id,
            "title": item.get("subject") or item.get("title") or item["id"],
            "kind": "announcement",
            "body": _plain(item.get("body")),
            "created_at": item.get("creationDate") or item.get("createdDate"),
            "updated_at": item.get("modifiedDate"),
        } for item in self._pages(path)]

    def _contents(self, course_id: str) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        visited: set[str] = set()

        def walk(parent_id: str, parent_path: tuple[str, ...]) -> None:
            if parent_id in visited:
                return
            visited.add(parent_id)
            path = f"/learn/api/v1/courses/{course_id}/contents/{parent_id}/children?{_CHILD_QUERY}"
            for item in self._pages(path):
                item_id = str(item["id"])
                handler = str(item.get("contentHandler") or "")
                found.append({
                    "id": item_id,
                    "course_id": course_id,
                    "title": item.get("title") or item_id,
                    "kind": "assignment" if handler == "resource/x-bb-assignment" else "content",
                    "body": _plain(item.get("body")) or _plain(item.get("description")) or (_external_link_url(item, handler) if handler == "resource/x-bb-externallink" else None),
                    "due_at": item.get("dueDate"),
                    "updated_at": str(item["modifiedDate"]) if item.get("modifiedDate") is not None else None,
                    "content_path": parent_path,
                    "is_container": handler in {"resource/x-bb-folder", "resource/x-bb-lesson"},
                    "attachments": _attachments(item, handler, item_id),
                })
                if handler in {"resource/x-bb-folder", "resource/x-bb-lesson"}:
                    title = str(item.get("title") or item_id)
                    walk(item_id, parent_path + (f"{title}--{item_id}",))

        walk("ROOT", ())
        return found

    def _feedback(self, course_id: str, user_id: str) -> list[dict[str, Any]]:
        columns_path = (
            f"/learn/api/v1/courses/{course_id}/gradebook/columns?"
            "isExcludedFromCourseUserActivity=true&expand=associatedRubrics%2CcollectExternalSubmissions&includeInvisible=false"
        )
        grades_path = (
            f"/learn/api/v1/courses/{course_id}/gradebook/grades?"
            f"isExcludedFromCourseUserActivity=true&limit=100&userId={user_id}"
        )
        columns = {str(x["id"]): x for x in self.transport.get_json(columns_path).get("results", ())}
        output = []
        for item in self.transport.get_json(grades_path).get("results", ()):
            feedback = _plain(item.get("instructorFeedback"))
            if not feedback:
                continue
            column = columns.get(str(item.get("columnId")), {})
            output.append({
                "id": str(item["id"]),
                "course_id": course_id,
                "title": column.get("columnName") or column.get("name") or "Retroalimentación",
                "kind": "feedback",
                "body": feedback,
                "updated_at": item.get("lastOverrideDate") or item.get("modifiedDate"),
            })
        return output
