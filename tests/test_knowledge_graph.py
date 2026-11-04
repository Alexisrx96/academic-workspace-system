from pathlib import Path

from academic_workspace.rag import build_rag_context


def test_graph_hybrid_expands_explicit_source_relation(tmp_path: Path):
    source = tmp_path / "Blackboard" / "SINF" / "source.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Decisiones\nLa información apoya decisiones gerenciales.\n", encoding="utf-8")
    note = tmp_path / "SINF" / "apunte.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        '---\nsource_ref: "[[Blackboard/SINF/source]]"\n---\n\n# Apunte\nMi explicación sobre decisiones.\n',
        encoding="utf-8",
    )

    result = build_rag_context(tmp_path, "decisiones gerenciales", mode="graph-hybrid", max_chunks=4)

    assert result["graph"]["enabled"] is True
    assert result["graph"]["expanded_count"] >= 1
    assert any(source["retrieval"] == "graph" for source in result["sources"])
    assert all(source["lane"] in {"official", "work"} for source in result["sources"])


def test_graph_hybrid_is_deterministic_and_bounded(tmp_path: Path):
    source = tmp_path / "Blackboard" / "SINF" / "source.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Decisiones\nLa información apoya decisiones.\n", encoding="utf-8")
    note = tmp_path / "SINF" / "apunte.md"
    note.parent.mkdir(parents=True)
    note.write_text('source_ref: "[[Blackboard/SINF/source]]"\n\n# Apunte\nDecisiones.\n', encoding="utf-8")

    first = build_rag_context(tmp_path, "decisiones", mode="graph-hybrid", max_chunks=2, max_chars=500)
    second = build_rag_context(tmp_path, "decisiones", mode="graph-hybrid", max_chunks=2, max_chars=500)

    assert first == second
    assert len(first["context"]) <= 500
    assert first["graph"]["max_nodes"] == 12
