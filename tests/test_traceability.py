from pathlib import Path

from academic_workspace.traceability import build_traceability_report


def test_traceability_reports_source_ref_coverage_without_editing_notes(tmp_path: Path):
    control = tmp_path / "Control Académico"
    control.mkdir(parents=True)
    (control / "Mapa de cursos.json").write_text(
        '{"format": 1, "courses": {"SINF-V02-022026": {"workspace": "SINF"}}}',
        encoding="utf-8",
    )
    linked = tmp_path / "SINF" / "Apunte vinculado.md"
    unlinked = tmp_path / "SINF" / "Borrador.md"
    linked.parent.mkdir(parents=True)
    linked.write_text(
        '---\nnote_kind: personal_note\nsource_ref: "[[Blackboard/SINF/index|Fuente]]"\n---\n\n# Apunte\n',
        encoding="utf-8",
    )
    unlinked.write_text('---\nnote_kind: personal_note\n---\n\n# Borrador\n', encoding="utf-8")
    before = {path: path.read_bytes() for path in (linked, unlinked)}

    report = build_traceability_report(tmp_path)

    assert "SINF-V02-022026" in report
    assert "Notas auditables: 2" in report
    assert "Con fuente explícita: 1" in report
    assert "Sin fuente explícita: 1" in report
    assert {path: path.read_bytes() for path in (linked, unlinked)} == before
