from pathlib import Path

from academic_workspace.rag import build_rag_context


def test_rag_lexical_fallback_recovers_broad_natural_query(tmp_path: Path):
    note = tmp_path / "Blackboard" / "SINF" / "decision.md"
    note.parent.mkdir(parents=True)
    note.write_text("# Decisiones\n\nLos sistemas de información apoyan decisiones estratégicas.\n", encoding="utf-8")

    result = build_rag_context(tmp_path, "cómo apoyan los sistemas de información las decisiones", mode="lexical")

    assert result["sources"]


def test_rag_context_is_deterministic_and_citable(tmp_path: Path):
    note = tmp_path / "Blackboard" / "SINF" / "decision.md"
    note.parent.mkdir(parents=True)
    note.write_text("# Decisiones\n\nLa información mejora la decisión gerencial.\n", encoding="utf-8")

    first = build_rag_context(tmp_path, "decisión gerencial", mode="lexical", max_chars=2000)
    second = build_rag_context(tmp_path, "decisión gerencial", mode="lexical", max_chars=2000)

    assert first == second
    assert first["sources"][0]["citation"] == "[S1]"
    assert "[S1]" in first["context"]
    assert first["token_estimate"] > 0


def test_rag_context_obeys_character_budget(tmp_path: Path):
    note = tmp_path / "Blackboard" / "SINF" / "long.md"
    note.parent.mkdir(parents=True)
    note.write_text("# Decisiones\n\n" + ("Información para decisiones. " * 200), encoding="utf-8")

    result = build_rag_context(tmp_path, "decisiones", mode="lexical", max_chars=500)

    assert len(result["context"]) <= 500
    assert result["sources"]
