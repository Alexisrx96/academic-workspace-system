from pathlib import Path

from academic_workspace.semantic_search import (
    rebuild_semantic_index,
    semantic_search,
)


class KeywordEmbeddingProvider:
    model_id = "keyword-v1"

    def encode(self, texts):
        return [
            [1.0, 0.0] if "decisión" in text.lower() or "decision" in text.lower() else [0.0, 1.0]
            for text in texts
        ]


def test_semantic_repository_indexes_chunks_and_exposes_scores(tmp_path: Path):
    note = tmp_path / "Blackboard" / "SINF" / "decision.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        "# Decisiones\n\n" + "La decisión gerencial requiere información. " * 30 + "\n\n"
        "## Contexto\n\n" + "El contexto estratégico explica la organización. " * 30,
        encoding="utf-8",
    )

    database = rebuild_semantic_index(tmp_path, KeywordEmbeddingProvider(), chunk_chars=240)
    results = semantic_search(tmp_path, "toma de decisión", KeywordEmbeddingProvider(), database=database)

    assert results
    assert results[0].path == "Blackboard/SINF/decision.md"
    assert results[0].score is not None
    assert results[0].chunk_id


def test_semantic_repository_reuses_unchanged_embeddings(tmp_path: Path):
    note = tmp_path / "Blackboard" / "SINF" / "decision.md"
    note.parent.mkdir(parents=True)
    note.write_text("# Decisiones\nLa decisión gerencial requiere información.\n", encoding="utf-8")
    provider = KeywordEmbeddingProvider()

    database = rebuild_semantic_index(tmp_path, provider)
    first = semantic_search(tmp_path, "decisión", provider, database=database)
    rebuild_semantic_index(tmp_path, provider, database=database)
    second = semantic_search(tmp_path, "decisión", provider, database=database)

    assert first[0].chunk_id == second[0].chunk_id
    assert first[0].content_hash == second[0].content_hash
