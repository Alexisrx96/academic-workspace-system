from pathlib import Path

from academic_workspace.academic_alerts import build_candidates


def test_build_candidates_uses_stable_keys_for_dashboard_links(tmp_path: Path):
    control = tmp_path / "Control Académico"
    control.mkdir(parents=True)
    (control / "00 - Dashboard académico.md").write_text(
        "# Dashboard académico\n\n"
        "## Atención ahora\n\n"
        "- [ ] **2026-08-20** · [Entrega](../Blackboard/SINF/Contenido/Entrega.md) — SINF\n"
        "\n## Vistas de control\n",
        encoding="utf-8",
    )

    candidates = build_candidates(tmp_path)

    assert len(candidates) == 1
    assert candidates[0].key == "dashboard:Blackboard/SINF/Contenido/Entrega.md"
    assert candidates[0].severity == "high"


def test_build_candidates_alerts_only_on_sync_failure_or_staleness(tmp_path: Path):
    control = tmp_path / "Control Académico"
    control.mkdir(parents=True)
    (control / "00 - Dashboard académico.md").write_text(
        "# Dashboard académico\n\n> Blackboard verificado\n\n## Atención ahora\n\n> No hay acciones nuevas priorizadas.\n",
        encoding="utf-8",
    )
    (tmp_path / ".blackboard-sync").mkdir()
    (tmp_path / ".blackboard-sync" / "sync-health.json").write_text(
        '{"format": 1, "sync_status": "unavailable", "last_blackboard_sync": null}\n',
        encoding="utf-8",
    )

    candidates = build_candidates(tmp_path)

    assert [candidate.key for candidate in candidates] == ["health:unavailable"]
    assert candidates[0].severity == "high"
