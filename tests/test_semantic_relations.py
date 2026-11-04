from pathlib import Path
import sqlite3

from academic_workspace.resource_registry import rebuild_resource_registry, add_semantic_relations
from academic_workspace.semantic_search import rebuild_semantic_index


class RelationEmbeddingProvider:
    model_id = "relation-v1"

    def encode(self, texts):
        vectors = []
        for text in texts:
            lower = text.lower()
            vectors.append([1.0, 0.0] if "decisión" in lower or "decision" in lower else [0.0, 1.0])
        return vectors


def test_semantic_relations_are_suggestions_with_confidence(tmp_path: Path):
    official = tmp_path / "Blackboard" / "SINF" / "decision.md"
    official.parent.mkdir(parents=True)
    official.write_text("# Decisiones\nLa decisión gerencial usa información.\n", encoding="utf-8")
    external = tmp_path / "Recursos Externos" / "support.md"
    external.parent.mkdir(parents=True)
    external.write_text("# Apoyo\nEl apoyo explica la decisión empresarial.\n", encoding="utf-8")
    unrelated = tmp_path / "Recursos Externos" / "unrelated.md"
    unrelated.write_text("# Otro\nCircuitos eléctricos y diodos.\n", encoding="utf-8")

    provider = RelationEmbeddingProvider()
    registry = rebuild_resource_registry(tmp_path)
    semantic = rebuild_semantic_index(tmp_path, provider)
    added = add_semantic_relations(registry, semantic, provider, threshold=0.9, top_k=2)

    assert added >= 1
    with sqlite3.connect(registry) as connection:
        rows = connection.execute(
            "SELECT relation_type, from_path, to_path, confidence FROM relations WHERE relation_type = 'semantic_related'"
        ).fetchall()

    assert rows
    assert all(row[3] >= 0.9 for row in rows)
    assert any("decision.md" in row[1] and "support.md" in row[2] for row in rows)
    assert not any("unrelated.md" in row[2] for row in rows)
