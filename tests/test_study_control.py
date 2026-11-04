from datetime import datetime, timezone
from pathlib import Path
import json

from academic_workspace.study_control import refresh_control


def _note(path: Path, *, title: str, kind: str = "assignment", due_at: str = "", updated_at: str = "2026-08-16T12:00:00Z") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'''---
blackboard_id: "{path.stem}"
course_id: "c1"
kind: "{kind}"
due_at: "{due_at}"
updated_at: "{updated_at}"
source: "Blackboard Ultra"
---

# {title}
''',
        encoding="utf-8",
    )


def test_control_baselines_existing_notes_then_reports_new_publications_and_calendar_due_dates(tmp_path: Path):
    target = tmp_path
    _note(
        target / "Blackboard" / "Curso" / "Contenido" / "Tarea--a1.md",
        title="Tarea de la semana",
        due_at="2026-08-18T23:59:00Z",
    )
    now = datetime(2026, 8, 16, 12, tzinfo=timezone.utc)

    first = refresh_control(target, now=now, days=7)

    assert first.baseline_created
    assert first.new_publications == ()
    assert [item.title for item in first.pending] == ["Tarea de la semana"]
    calendar = (target / "Control Académico" / "UTEC-Fechas.ics").read_text(encoding="utf-8")
    assert "SUMMARY:Tarea de la semana" in calendar
    assert "TRIGGER:-PT24H" in calendar

    _note(target / "Blackboard" / "Curso" / "Anuncios" / "Anuncio--a2.md", title="Nueva publicación", kind="announcement")
    second = refresh_control(target, now=now, days=7)

    assert not second.baseline_created
    assert [item.title for item in second.new_publications] == ["Nueva publicación"]
    assert "Nueva publicación" in (target / "Control Académico" / "Estado semanal.md").read_text(encoding="utf-8")


def test_control_report_keeps_actionable_publications_and_hides_technical_duplicates(tmp_path: Path):
    target = tmp_path
    now = datetime(2026, 8, 16, 12, tzinfo=timezone.utc)
    _note(target / "Blackboard" / "Curso" / "Contenido" / "Semana--s1" / "index.md", title="Semana 1")
    _note(target / "Blackboard" / "Curso" / "Contenido" / "Semana--s1" / "Clases--c1" / "index.md", title="Clases")
    _note(target / "Blackboard" / "Curso" / "Contenido" / "Semana--s1" / "Clases--c1" / "Clase real--d1" / "index.md", title="Clase real")
    _note(target / "Blackboard" / "Curso" / "Contenido" / "Semana--s1" / "Clases--c1" / "Clase real--d1" / "ultraDocumentBody--d2.md", title="ultraDocumentBody")
    refresh_control(target, now=now)

    _note(target / "Blackboard" / "Curso" / "Contenido" / "Semana--s1" / "index.md", title="Semana 1", updated_at="2026-08-17T12:00:00Z")
    _note(target / "Blackboard" / "Curso" / "Contenido" / "Semana--s1" / "Clases--c1" / "index.md", title="Clases", updated_at="2026-08-17T12:00:00Z")
    _note(target / "Blackboard" / "Curso" / "Contenido" / "Semana--s1" / "Clases--c1" / "Clase real--d1" / "index.md", title="Clase real", updated_at="2026-08-17T12:00:00Z")
    _note(target / "Blackboard" / "Curso" / "Contenido" / "Semana--s1" / "Clases--c1" / "Clase real--d1" / "ultraDocumentBody--d2.md", title="ultraDocumentBody", updated_at="2026-08-17T12:00:00Z")
    second = refresh_control(target, now=now)

    assert [item.title for item in second.new_publications] == ["Clase real"]
    report = (target / "Control Académico" / "Estado semanal.md").read_text(encoding="utf-8")
    assert "Clase real" in report
    assert "ultraDocumentBody" not in report
    assert "**Clases**" not in report


def test_control_reports_textual_dates_without_creating_calendar_events(tmp_path: Path):
    target = tmp_path
    now = datetime(2026, 8, 16, 12, tzinfo=timezone.utc)
    path = target / "Blackboard" / "Curso" / "Anuncios" / "Parcial--a1.md"
    _note(path, title="Evaluación parcial", kind="announcement")
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "# Evaluación parcial\n",
            "# Evaluación parcial\n\nEl examen será el jueves 20 de agosto de 2026. El diferido será el 03 de septiembre de 2026.\n",
        ),
        encoding="utf-8",
    )
    refresh_control(target, now=now)
    path.write_text(path.read_text(encoding="utf-8") + "\nActualización publicada.\n", encoding="utf-8")

    refresh_control(target, now=now)

    report = (target / "Control Académico" / "Estado semanal.md").read_text(encoding="utf-8")
    calendar = (target / "Control Académico" / "UTEC-Fechas.ics").read_text(encoding="utf-8")
    assert "## Fechas mencionadas, pendientes de confirmación" in report
    assert "20 de agosto de 2026" in report
    assert "03 de septiembre de 2026" in report
    assert report.count("20 de agosto de 2026") == 1
    assert "SUMMARY:Evaluación parcial" not in calendar


def test_control_generates_global_domain_matrix_without_editing_course_journal(tmp_path: Path):
    target = tmp_path
    journal = target / "Proyectos de Estudio" / "SINF - Parcial 1" / "Bitácora de dominio.md"
    journal.parent.mkdir(parents=True, exist_ok=True)
    journal.write_text(
        "# SINF — Bitácora de dominio\n\n"
        "| Fecha | Bloque | Explicación sin apuntes (0–3) | Aplicación (0–3) | Error/duda concreta | Próxima acción |\n"
        "|---|---|---:|---:|---|---|\n"
        "| 2026-08-16 | Sistemas de información y SIG | 2 | 1 | Confundo SIG y SI | Resolver caso |\n",
        encoding="utf-8",
    )

    from academic_workspace.study_control import refresh_control

    refresh_control(target, now=datetime(2026, 8, 16, 12, tzinfo=timezone.utc))

    matrix = (target / "Control Académico" / "Matriz de dominio.md").read_text(encoding="utf-8")
    assert "SINF" in matrix
    assert "Sistemas de información y SIG" in matrix
    assert "2/3" in matrix
    assert "1/3" in matrix
    assert "Resolver caso" in matrix
    assert journal.read_text(encoding="utf-8").count("Resolver caso") == 1


def test_control_generates_academic_dashboard_with_actionable_links(tmp_path: Path):
    target = tmp_path
    now = datetime(2026, 8, 16, 12, tzinfo=timezone.utc)
    _note(
        target / "Blackboard" / "Entrega" / "Contenido" / "Tarea--a1.md",
        title="Entrega prioritaria",
        kind="assignment",
        due_at="2026-08-18T23:59:00Z",
    )
    project = target / "Proyectos de Estudio" / "Curso - Parcial 1" / "Bitácora de dominio.md"
    project.parent.mkdir(parents=True, exist_ok=True)
    project.write_text(
        "# Curso — Bitácora de dominio\n\n"
        "| Fecha | Bloque | Explicación sin apuntes (0–3) | Aplicación (0–3) | Error/duda concreta | Próxima acción |\n"
        "|---|---|---:|---:|---|---|\n"
        "| 2026-08-16 | Bloque débil | 1 | 0 | Falta práctica | Resolver ejercicio |\n",
        encoding="utf-8",
    )

    refresh_control(target, now=now, days=7)

    dashboard = (target / "Control Académico" / "00 - Dashboard académico.md").read_text(encoding="utf-8")
    assert "# Dashboard académico" in dashboard
    assert "Entrega prioritaria" in dashboard
    assert "Matriz de dominio" in dashboard
    assert "Estado semanal" in dashboard
    assert "Última actualización local" in dashboard
    assert "Bloque débil" in dashboard


def test_control_persists_local_and_academic_workspace_health_separately(tmp_path: Path):
    target = tmp_path
    first_now = datetime(2026, 8, 16, 12, tzinfo=timezone.utc)

    refresh_control(target, now=first_now)
    health_path = target / ".blackboard-sync" / "sync-health.json"
    initial = json.loads(health_path.read_text(encoding="utf-8"))
    assert initial["sync_status"] == "unverified"
    assert initial["last_blackboard_sync"] is None
    assert initial["last_local_refresh"] == "2026-08-16T12:00:00+00:00"

    refresh_control(target, now=first_now, sync_status="verified")
    verified = json.loads(health_path.read_text(encoding="utf-8"))
    assert verified["sync_status"] == "verified"
    assert verified["last_blackboard_sync"] == "2026-08-16T12:00:00+00:00"

    later = datetime(2026, 8, 18, 12, tzinfo=timezone.utc)
    refresh_control(target, now=later)
    local_only = json.loads(health_path.read_text(encoding="utf-8"))
    assert local_only["sync_status"] == "verified"
    assert local_only["last_blackboard_sync"] == "2026-08-16T12:00:00+00:00"
    assert local_only["last_local_refresh"] == "2026-08-18T12:00:00+00:00"

    refresh_control(target, now=later, sync_status="unavailable")
    unavailable = json.loads(health_path.read_text(encoding="utf-8"))
    assert unavailable["sync_status"] == "unavailable"
    assert unavailable["last_blackboard_sync"] == "2026-08-16T12:00:00+00:00"
    dashboard = (target / "Control Académico" / "00 - Dashboard académico.md").read_text(encoding="utf-8")
    assert "Fuente académica no disponible" in dashboard


def test_control_reads_configured_non_blackboard_source_lane(tmp_path: Path):
    config = tmp_path / ".blackboard-sync" / "sources.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        '{"format": 1, "sources": [{"provider": "fixture", "instance": "demo", "root": "Fuentes/Fixture"}]}',
        encoding="utf-8",
    )
    note = tmp_path / "Fuentes" / "Fixture" / "Demo" / "Anuncios" / "Aviso--a1.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(
        "---\nsource_provider: \"fixture\"\nsource_instance: \"demo\"\nkind: \"announcement\"\n"
        "due_at: \"2026-08-18T23:59:00Z\"\nupdated_at: \"2026-08-16T12:00:00Z\"\n---\n\n# Aviso fixture\n",
        encoding="utf-8",
    )

    result = refresh_control(tmp_path, now=datetime(2026, 8, 16, 12, tzinfo=timezone.utc), days=7)

    assert [item.title for item in result.pending] == ["Aviso fixture"]
    assert "Aviso fixture" in (tmp_path / "Control Académico" / "Estado semanal.md").read_text(encoding="utf-8")
    target = tmp_path
    personal_files = {
        target / "SINF" / "Apunte propio.md": "# Mi explicación\n\nNo tocar.\n",
        target / "LEMA" / "Tarea" / "Borrador.md": "# Borrador\n\nContenido personal.\n",
        target / "Proyectos de Estudio" / "SINF - Parcial 1" / "Proyecto de dominio.md": "# Práctica\n\nCaso propio.\n",
    }
    for path, content in personal_files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    before = {path: path.read_bytes() for path in personal_files}

    refresh_control(target, now=datetime(2026, 8, 16, 12, tzinfo=timezone.utc))

    assert {path: path.read_bytes() for path in personal_files} == before


def test_control_prioritizes_upcoming_domain_review(tmp_path: Path):
    journal = tmp_path / "Proyectos de Estudio" / "SINF - Parcial 1" / "Bitácora de dominio.md"
    journal.parent.mkdir(parents=True)
    journal.write_text(
        "# Bitácora\n\n"
        "| Fecha | Bloque | Explicación sin apuntes (0–3) | Aplicación (0–3) | Error/duda concreta | Próxima acción | Próximo repaso |\n"
        "|---|---|---:|---:|---|---|---|\n"
        "| 2026-08-18 | SIG | 2 | 2 | — | Recuperar concepto | 2026-08-20 |\n",
        encoding="utf-8",
    )

    refresh_control(tmp_path, now=datetime(2026, 8, 18, 12, tzinfo=timezone.utc))

    dashboard = (tmp_path / "Control Académico" / "00 - Dashboard académico.md").read_text(encoding="utf-8")
    assert "SINF — repaso" in dashboard
    assert "2026-08-20" in dashboard
