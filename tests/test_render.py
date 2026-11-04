from pathlib import Path

from academic_workspace.models import Snapshot
from academic_workspace.render import refresh_manifest, render_snapshot


def test_render_is_idempotent_and_never_creates_grade_files(tmp_path: Path):
    snapshot = Snapshot.from_mapping({
        "courses": [{"id": "_c_", "course_id": "SINF-V02", "name": "Sistemas"}],
        "activities": [
            {"id": "a1", "course_id": "_c_", "kind": "announcement", "title": "Aviso", "body": "Hola"},
            {"id": "t1", "course_id": "_c_", "kind": "assignment", "title": "Tarea 1", "due_at": "2026-08-20T23:59:00Z"},
            {"id": "f1", "course_id": "_c_", "kind": "feedback", "title": "Tarea 1", "body": "Mejorar conclusión"},
        ],
    })

    first = render_snapshot(snapshot, tmp_path)
    second = render_snapshot(snapshot, tmp_path)

    assert first.changed
    assert not second.changed
    assert first.manifest_hash == second.manifest_hash
    files = sorted(str(path.relative_to(tmp_path)).replace("\\", "/") for path in tmp_path.rglob("*.*") if path.is_file())
    assert files == [
        ".blackboard-sync/manifest.json",
        "Blackboard/SINF-V02/Actividades/Tarea 1--t1.md",
        "Blackboard/SINF-V02/Anuncios/Aviso--a1.md",
        "Blackboard/SINF-V02/Retroalimentacion/Tarea 1--f1.md",
        "Blackboard/SINF-V02/index.md",
    ]
    assert not any("calific" in name.lower() or "grade" in name.lower() for name in files)


def test_refresh_manifest_includes_post_render_managed_files(tmp_path: Path):
    snapshot = Snapshot.from_mapping({
        "courses": [{"id": "c1", "course_id": "ADCC", "name": "Administración"}],
        "activities": [],
    })
    render_snapshot(snapshot, tmp_path)
    index = tmp_path / "Blackboard" / "ADCC" / "index.md"
    index.write_text(index.read_text(encoding="utf-8") + "\nCanva", encoding="utf-8")
    slide = tmp_path / "Blackboard" / "ADCC" / "Recursos Canva" / "Diapositivas" / "demo" / "slide-001.png"
    slide.parent.mkdir(parents=True)
    slide.write_bytes(b"png")

    refresh_manifest(tmp_path)

    import hashlib, json
    manifest = json.loads((tmp_path / ".blackboard-sync" / "manifest.json").read_text(encoding="utf-8"))
    entries = {entry["path"]: entry["sha256"] for entry in manifest["files"]}
    assert "Blackboard/ADCC/Recursos Canva/Diapositivas/demo/slide-001.png" in entries
    assert entries["Blackboard/ADCC/index.md"] == hashlib.sha256(index.read_bytes()).hexdigest()


def test_render_supports_an_alternative_source_lane_and_provider_metadata(tmp_path: Path):
    snapshot = Snapshot.from_mapping({
        "courses": [{"id": "c1", "course_id": "MATH-1", "name": "Matemática"}],
        "activities": [{"id": "a1", "course_id": "c1", "kind": "content", "title": "Unidad 1"}],
    })

    render_snapshot(
        snapshot,
        tmp_path,
        source_root="Fuentes/Moodle",
        source_provider="moodle",
        source_instance="utec",
    )

    note = tmp_path / "Fuentes" / "Moodle" / "MATH-1" / "Contenido" / "Unidad 1--a1.md"
    course = tmp_path / "Fuentes" / "Moodle" / "MATH-1" / "index.md"
    assert note.is_file()
    assert course.is_file()
    assert 'source_provider: "moodle"' in note.read_text(encoding="utf-8")
    assert 'source_instance: "utec"' in course.read_text(encoding="utf-8")
