import json
from pathlib import Path

from academic_workspace.memory import SqliteMemoryStore, memory_store_for_workspace
from academic_workspace.workspace_commands import init_workspace


def test_sqlite_memory_is_versioned_and_idempotent(tmp_path: Path):
    store = SqliteMemoryStore(tmp_path / "memory.sqlite3")
    store.append_once("event-1", {"type": "study", "topic": "SIG"})
    store.append_once("event-1", {"type": "study", "topic": "changed"})

    assert store.events() == [{"event_id": "event-1", "type": "study", "topic": "SIG"}]
    import sqlite3
    with sqlite3.connect(tmp_path / "memory.sqlite3") as connection:
        assert connection.execute("SELECT value FROM metadata WHERE key = 'schema_version'").fetchone() == ("1",)


def test_configured_sqlite_imports_legacy_jsonl_once(tmp_path: Path):
    init_workspace(tmp_path)
    legacy = tmp_path / ".blackboard-sync" / "evidence.jsonl"
    legacy.write_text(json.dumps({"event_id": "legacy-1", "type": "evidence", "course": "SINF"}) + "\n", encoding="utf-8")

    first = memory_store_for_workspace(tmp_path)
    second = memory_store_for_workspace(tmp_path)

    expected = [{"event_id": "legacy-1", "type": "evidence", "course": "SINF"}]
    assert first.events() == expected
    assert second.events() == expected
    assert (tmp_path / ".blackboard-sync" / "memory.sqlite3").is_file()


def test_jsonl_backend_remains_available(tmp_path: Path):
    init_workspace(tmp_path)
    config_path = tmp_path / ".blackboard-sync" / "workspace-config.json"
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload["memory"]["backend"] = "jsonl"
    config_path.write_text(json.dumps(payload), encoding="utf-8")

    store = memory_store_for_workspace(tmp_path)
    store.append_once("jsonl-1", {"type": "study"})

    assert store.events()[0]["event_id"] == "jsonl-1"
    assert (tmp_path / ".blackboard-sync" / "evidence.jsonl").is_file()
