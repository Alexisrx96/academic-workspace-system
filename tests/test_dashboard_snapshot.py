import json
from pathlib import Path

from academic_workspace.dashboard_snapshot import build_snapshot


def test_dashboard_snapshot_is_stable_and_excludes_volatile_local_time(tmp_path: Path):
    control = tmp_path / "Control Académico"
    control.mkdir(parents=True)
    (control / "00 - Dashboard académico.md").write_text(
        "# Dashboard académico\n\n"
        "> Última actualización local: 2026-08-18 12:00\n"
        "> **Fuente académica verificada:** última sincronización: 2026-08-18T10:00:00+00:00.\n\n"
        "## Atención ahora\n\n"
        "- [ ] **2026-08-20** · [Tarea](../Blackboard/SINF/Tarea.md) — SINF\n\n"
        "## Vistas de control\n",
        encoding="utf-8",
    )
    (tmp_path / ".blackboard-sync").mkdir()
    (tmp_path / ".blackboard-sync" / "sync-health.json").write_text(
        '{"format": 1, "sync_status": "verified", "last_local_refresh": "volatile", '
        '"last_blackboard_sync": "2026-08-18T10:00:00+00:00"}\n',
        encoding="utf-8",
    )
    first = build_snapshot(tmp_path)
    (control / "00 - Dashboard académico.md").write_text(
        (control / "00 - Dashboard académico.md").read_text(encoding="utf-8").replace("2026-08-18 12:00", "2026-08-18 13:00"),
        encoding="utf-8",
    )
    second = build_snapshot(tmp_path)

    assert first == second
    assert first["health"]["last_local_refresh"] is None
    assert first["attention"][0]["source"] == "Blackboard/SINF/Tarea.md"
