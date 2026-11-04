from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Protocol

from .workspace_commands import load_workspace_config


class MemoryStore(Protocol):
    def append_once(self, event_id: str, payload: dict[str, Any]) -> None: ...
    def events(self) -> list[dict[str, Any]]: ...


class JsonlMemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def append_once(self, event_id: str, payload: dict[str, Any]) -> None:
        existing = {event.get("event_id") for event in self.events()}
        if event_id in existing:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps({"event_id": event_id, **payload}, ensure_ascii=False, sort_keys=True) + "\n")

    def events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        result = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                result.append(value)
        return result


class SqliteMemoryStore:
    schema_version = 1

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS events (event_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            connection.execute("INSERT OR IGNORE INTO metadata(key, value) VALUES ('schema_version', ?)", (str(self.schema_version),))
            connection.commit()

    def append_once(self, event_id: str, payload: dict[str, Any]) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute("INSERT OR IGNORE INTO events(event_id, payload) VALUES (?, ?)", (event_id, json.dumps({"event_id": event_id, **payload}, ensure_ascii=False, sort_keys=True)))
            connection.commit()

    def append_session_state(self, event_id: str, payload: dict[str, Any]) -> None:
        """Atomically compare and append a versioned session snapshot."""
        with sqlite3.connect(self.path, timeout=30, isolation_level=None) as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute("SELECT payload FROM events ORDER BY rowid").fetchall()
            current: dict[str, Any] | None = None
            for row in rows:
                event = json.loads(row[0])
                if event.get("schema") != "study-session.v1" or event.get("session_id") != payload.get("session_id"):
                    continue
                if current is None or int(event.get("revision", 0)) >= int(current.get("revision", 0)):
                    current = event
            if current is not None:
                current_payload = {key: value for key, value in current.items() if key != "event_id"}
                if current_payload == payload:
                    connection.commit()
                    return
                if int(payload.get("revision", 0)) <= int(current.get("revision", 0)):
                    connection.rollback()
                    raise ValueError("transición de sesión obsoleta o conflictiva")
            connection.execute(
                "INSERT OR IGNORE INTO events(event_id, payload) VALUES (?, ?)",
                (event_id, json.dumps({"event_id": event_id, **payload}, ensure_ascii=False, sort_keys=True)),
            )
            connection.commit()

    def events(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute("SELECT payload FROM events ORDER BY rowid").fetchall()
        return [json.loads(row[0]) for row in rows]

    def import_jsonl(self, path: Path) -> int:
        imported = 0
        legacy = JsonlMemoryStore(path)
        for event in legacy.events():
            event_id = str(event.get("event_id", ""))
            if not event_id:
                continue
            payload = {key: value for key, value in event.items() if key != "event_id"}
            before = len(self.events())
            self.append_once(event_id, payload)
            imported += int(len(self.events()) > before)
        return imported


class CallbackMemoryStore:
    """Adapter for a harness-owned memory backend."""
    def __init__(self, append_once, events):
        self._append = append_once
        self._events = events

    def append_once(self, event_id: str, payload: dict[str, Any]) -> None:
        self._append(event_id, payload)

    def events(self) -> list[dict[str, Any]]:
        return list(self._events())


class ObsidianMemoryStore:
    def __init__(self, vault: Path, relative_root: str = "Control Académico/Evidencia") -> None:
        self.root = Path(vault) / relative_root

    def append_once(self, event_id: str, payload: dict[str, Any]) -> None:
        path = self.root / f"{event_id}.md"
        if path.exists():
            return
        self.root.mkdir(parents=True, exist_ok=True)
        title = payload.get("topic") or payload.get("course") or "Evidencia de estudio"
        content = "---\n" + f"event_id: {json.dumps(event_id, ensure_ascii=False)}\n" + "note_kind: evidence_record\n" + f"course: {json.dumps(payload.get('course', ''), ensure_ascii=False)}\n" + f"topic: {json.dumps(payload.get('topic', ''), ensure_ascii=False)}\n---\n\n" + f"# {title}\n\n```json\n" + json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n```\n"
        path.write_text(content, encoding="utf-8", newline="\n")

    def events(self) -> list[dict[str, Any]]:
        result = []
        for path in sorted(self.root.glob("*.md")) if self.root.exists() else ():
            match = re.search(r"```json\n(.*?)\n```", path.read_text(encoding="utf-8", errors="replace"), re.DOTALL)
            if not match:
                continue
            try:
                value = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
            value["event_id"] = path.stem
            result.append(value)
        return result


class HttpMemoryStore:
    """Distributed memory adapter; transport is injected for security and testing."""
    def __init__(self, request):
        self._request = request

    def append_once(self, event_id: str, payload: dict[str, Any]) -> None:
        self._request("POST", "/events", {"event_id": event_id, **payload})

    def events(self) -> list[dict[str, Any]]:
        return list(self._request("GET", "/events", None) or [])


class SqliteVectorMemoryStore(SqliteMemoryStore):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        with sqlite3.connect(self.path) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS event_vectors (event_id TEXT PRIMARY KEY, vector BLOB NOT NULL)")
            connection.commit()

    def put_vector(self, event_id: str, vector: list[float]) -> None:
        import struct
        with sqlite3.connect(self.path) as connection:
            connection.execute("INSERT OR REPLACE INTO event_vectors(event_id, vector) VALUES (?, ?)", (event_id, struct.pack(f"<{len(vector)}f", *vector)))
            connection.commit()

    def similar(self, vector: list[float], limit: int = 10) -> list[tuple[dict[str, Any], float]]:
        import math
        import struct
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute("SELECT event_id, vector FROM event_vectors").fetchall()
        events = {item.get("event_id"): item for item in self.events()}
        ranked = []
        for event_id, blob in rows:
            values = list(struct.unpack(f"<{len(blob)//4}f", blob))
            denominator = math.sqrt(sum(x*x for x in vector) * sum(x*x for x in values))
            score = sum(a*b for a,b in zip(vector, values)) / denominator if denominator else 0.0
            ranked.append((events.get(event_id, {}), score))
        return sorted(ranked, key=lambda item: -item[1])[:limit]


def memory_store_for_workspace(target: Path, *, backend: str | None = None) -> MemoryStore:
    """Select the configured local backend and import legacy JSONL once."""
    target = Path(target)
    config_path = target / ".blackboard-sync" / "workspace-config.json"
    config = load_workspace_config(target).memory
    selected = backend or (config.backend if config_path.is_file() else "jsonl")
    if selected == "jsonl":
        return JsonlMemoryStore(target / ".blackboard-sync" / "evidence.jsonl")
    if selected != "sqlite":
        raise ValueError(f"backend de memoria no soportado: {selected}")
    database = Path(config.database)
    if not database.is_absolute():
        database = target / database
    store = SqliteMemoryStore(database)
    if config.import_legacy_jsonl:
        store.import_jsonl(target / ".blackboard-sync" / "evidence.jsonl")
    return store
