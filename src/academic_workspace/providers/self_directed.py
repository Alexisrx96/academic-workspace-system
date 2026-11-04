from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import re

from .contracts import SourceCapabilities, SourceCourse, SourceHealth, SourceIdentity, SourceItem, SourceSnapshot, parse_datetime


class SelfDirectedProvider:
    provider_id = "self_directed"

    def __init__(self, root: Path, *, instance: str) -> None:
        self.root = Path(root)
        self.instance_id = instance

    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(courses=True, content=True, assignments=True, due_dates=True, attachments=True)

    def _metadata(self, text: str) -> dict[str, str]:
        if not text.startswith("---\n"):
            return {}
        end = text.find("\n---\n", 4)
        if end < 0:
            return {}
        values = {}
        for line in text[4:end].splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                values[key.strip()] = value.strip().strip('"')
        return values

    def collect_snapshot(self) -> SourceSnapshot:
        course_identity = SourceIdentity(self.provider_id, self.instance_id, self.instance_id)
        course = SourceCourse(course_identity, self.instance_id, self.root.name, {"kind": "self_directed"})
        items = []
        for path in sorted(self.root.rglob("*.md")) if self.root.exists() else ():
            text = path.read_text(encoding="utf-8", errors="replace")
            metadata = self._metadata(text)
            title_match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
            title = title_match.group(1) if title_match else path.stem
            body = text
            if text.startswith("---"):
                end = text.find("\n---\n", 4)
                if end >= 0:
                    body = text[end + 5 :]
            item_id = sha256(path.relative_to(self.root).as_posix().encode()).hexdigest()[:16]
            items.append(SourceItem(
                identity=SourceIdentity(self.provider_id, self.instance_id, item_id),
                course=course_identity,
                kind=metadata.get("kind", "lesson"),
                title=title,
                body=body.strip(),
                due_at=parse_datetime(metadata.get("due_at")),
                updated_at=parse_datetime(metadata.get("updated_at")),
                metadata={"path": path.relative_to(self.root).as_posix()},
            ))
        return SourceSnapshot(self.provider_id, self.instance_id, (course,), tuple(items))

    def health(self) -> SourceHealth:
        return SourceHealth("verified", datetime.now(timezone.utc).isoformat()) if self.root.is_dir() else SourceHealth("unavailable", datetime.now(timezone.utc).isoformat(), "source root missing")
