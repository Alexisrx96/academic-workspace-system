from pathlib import Path

from academic_workspace.empty_notes import quarantine_empty_notes


def test_quarantine_moves_only_review_leaves_and_removes_empty_dirs(tmp_path: Path):
    root = tmp_path / "Blackboard" / "LEMA-V01-022026"
    leaf_dir = root / "Contenido" / "Semana"
    leaf_dir.mkdir(parents=True)
    leaf = leaf_dir / "index.md"
    leaf.write_text("# Semana vacía\n", encoding="utf-8")
    container = root / "Contenido" / "Clase"
    container.mkdir(parents=True)
    (container / "index.md").write_text("# Clase\n", encoding="utf-8")
    (container / "real.md").write_text("# Real\nContenido.\n", encoding="utf-8")

    result = quarantine_empty_notes(tmp_path, "Blackboard/LEMA-V01-022026", run_id="test-run")

    assert result["moved_count"] == 1
    assert not leaf.exists()
    assert not leaf_dir.exists()
    assert (root / "Contenido" / "Clase" / "index.md").exists()
    assert (tmp_path / "_backups" / "pruned-empty" / "test-run" / "Blackboard" / "LEMA-V01-022026" / "Contenido" / "Semana" / "index.md").exists()
