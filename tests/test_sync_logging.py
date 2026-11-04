import json
import time

from academic_workspace.sync_logging import SyncLogger


def test_sync_logger_writes_events_and_heartbeat(tmp_path):
    with SyncLogger(tmp_path, heartbeat_seconds=0.01) as log:
        log.event("phase_started", phase="download", total=2)
        log.progress("download", current=1, total=2, item="a1")
        time.sleep(0.03)
        log.event("phase_finished", phase="download", current=2, total=2)

    records = [json.loads(line) for line in (tmp_path / ".blackboard-sync" / "sync.log").read_text(encoding="utf-8").splitlines()]
    assert records[0]["event"] == "run_started"
    assert any(record["event"] == "phase_started" and record["phase"] == "download" for record in records)
    assert any(record["event"] == "progress" and record["current"] == 1 for record in records)
    assert any(record["event"] == "heartbeat" for record in records)
    assert records[-1]["event"] == "run_finished"
    assert all(record["run_id"] == records[0]["run_id"] for record in records)


def test_sync_logger_preserves_blocked_final_status(tmp_path):
    log = SyncLogger(tmp_path, heartbeat_seconds=0.01)
    log.__enter__()
    log.set_status("blocked")
    log.__exit__(None, None, None)

    records = [json.loads(line) for line in (tmp_path / ".blackboard-sync" / "sync.log").read_text(encoding="utf-8").splitlines()]
    assert records[-1]["event"] == "run_finished"
    assert records[-1]["status"] == "blocked"
