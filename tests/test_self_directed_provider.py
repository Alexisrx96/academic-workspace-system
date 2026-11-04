from pathlib import Path

from academic_workspace.providers.self_directed import SelfDirectedProvider


def test_self_directed_provider_normalizes_local_learning_material(tmp_path: Path):
    root = tmp_path / "Fuentes" / "Autodidacta" / "Python-Advanced"
    root.mkdir(parents=True)
    (root / "decoradores.md").write_text(
        "---\nkind: lesson\ndue_at: 2026-08-20T23:59:00Z\n---\n\n# Decoradores\n\nExplican funciones de orden superior.\n",
        encoding="utf-8",
    )

    provider = SelfDirectedProvider(root, instance="python-advanced")
    snapshot = provider.collect_snapshot()

    assert provider.provider_id == "self_directed"
    assert snapshot.courses[0].identity.key == "self_directed:python-advanced:python-advanced"
    assert snapshot.items[0].title == "Decoradores"
    assert snapshot.items[0].kind == "lesson"
    assert snapshot.items[0].due_at is not None
    assert provider.health().status == "verified"
