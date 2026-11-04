import json

from academic_workspace import cli
from academic_workspace.workspace_commands import default_config, init_workspace


def test_study_search_requires_explicit_authorization(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(cli, "search_web", lambda query, authorized: [{"title": "Ejemplo", "url": "https://example.org/a"}] if authorized else [])

    assert cli.main(["study", "search", "--target", str(tmp_path), "--query", "ejemplo", "--authorized"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema"] == "web-search-results.v1"
    assert payload["hits"][0]["url"] == "https://example.org/a"


def test_study_search_respects_workspace_external_source_policy(monkeypatch, capsys, tmp_path):
    init_workspace(tmp_path)
    config = default_config().to_dict()
    config["privacy"]["allow_external_sources"] = False
    (tmp_path / ".blackboard-sync" / "workspace-config.json").write_text(json.dumps(config), encoding="utf-8")
    called = False

    def forbidden_search(*_args, **_kwargs):
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(cli, "search_web", forbidden_search)

    assert cli.main(["study", "search", "--target", str(tmp_path), "--query", "ejemplo", "--authorized"]) == 1
    assert called is False
    assert "fuentes externas" in capsys.readouterr().err
