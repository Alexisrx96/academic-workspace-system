from pathlib import Path

from academic_workspace.semantic_search import rebuild_semantic_index, semantic_search


class ToyEmbeddingProvider:
    model_id = "toy-v1"

    def encode(self, texts):
        return [[1.0, 0.0] if "decisión" in text.lower() or "decision" in text.lower() else [0.0, 1.0] for text in texts]


def test_semantic_index_uses_local_provider_and_preserves_provenance(tmp_path: Path):
    official = tmp_path / "Blackboard" / "SINF" / "decision.md"
    official.parent.mkdir(parents=True)
    official.write_text("# Decisiones\nApoya la decisión gerencial.\n", encoding="utf-8")
    external = tmp_path / "Recursos Externos" / "extra.md"
    external.parent.mkdir(parents=True)
    external.write_text("# Apoyo\nContexto adicional.\n", encoding="utf-8")
    provider = ToyEmbeddingProvider()

    database = rebuild_semantic_index(tmp_path, provider)
    results = semantic_search(tmp_path, "toma de decisión", provider, database=database)

    assert results[0].lane == "official"
    assert results[0].path == "Blackboard/SINF/decision.md"


def test_semantic_search_supports_filters(tmp_path: Path):
    path = tmp_path / "Blackboard" / "ELE1" / "diodos.md"
    path.parent.mkdir(parents=True)
    path.write_text("# Diodos\nRectificación.\n", encoding="utf-8")
    provider = ToyEmbeddingProvider()
    rebuild_semantic_index(tmp_path, provider)

    assert semantic_search(tmp_path, "diodos", provider, course="ELE1")[0].course == "ELE1"
