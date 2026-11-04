from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import os
import threading
import time
import uuid
from typing import Any


class SyncLogger:
    """Append-only JSONL diagnostics for long-running sync executions.

    The log is operational evidence, not a source artifact: it may contain
    timestamps and elapsed durations, but never browser URLs, cookies, or
    credentials. A heartbeat is emitted independently of the current phase so
    a quiet download/render operation is distinguishable from a dead process.
    """

    def __init__(self, target: Path, *, heartbeat_seconds: float = 30.0) -> None:
        self.target = Path(target)
        self.path = self.target / ".blackboard-sync" / "sync.log"
        self.run_id = uuid.uuid4().hex[:12]
        self.heartbeat_seconds = heartbeat_seconds
        self.started = time.monotonic()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._state: dict[str, Any] = {"phase": "starting", "current": 0, "total": None}
        self._result_status = "completed"

    def set_status(self, status: str) -> None:
        self._result_status = status
    def __enter__(self) -> "SyncLogger":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.event("run_started", phase="startup", pid=os.getpid())
        self._thread = threading.Thread(target=self._heartbeat_loop, name=f"sync-heartbeat-{self.run_id}", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, _tb) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.heartbeat_seconds))
        self.event("run_finished", phase=self._state.get("phase"), status="failed" if exc else self._result_status)

    def _heartbeat_loop(self) -> None:
        while not self._stop.wait(self.heartbeat_seconds):
            self.event("heartbeat", **self._state)

    def event(self, event: str, *, phase: str | None = None, **fields: Any) -> None:
        if phase is not None:
            self._state["phase"] = phase
        if "current" in fields:
            self._state["current"] = fields["current"]
        if "total" in fields:
            self._state["total"] = fields["total"]
        record: dict[str, Any] = {
            "schema": "sync-log.v1",
            "run_id": self.run_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "elapsed_seconds": round(time.monotonic() - self.started, 3),
            "event": event,
            "phase": self._state.get("phase"),
            **fields,
        }
        with self._lock:
            with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                stream.flush()

    def progress(
        self,
        phase: str,
        *,
        current: int,
        total: int | None = None,
        item: str | None = None,
        scope: str | None = None,
        unit: str | None = None,
        **extra_fields: Any,
    ) -> None:
        fields: dict[str, Any] = {"current": current}
        if total is not None:
            fields["total"] = total
        if item:
            fields["item_id"] = item
        if scope:
            fields["scope"] = scope
        if unit:
            fields["unit"] = unit
        fields.update(extra_fields)
        self.event("progress", phase=phase, **fields)
