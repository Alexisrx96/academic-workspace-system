from academic_workspace.differential import DifferentialCheck
from academic_workspace.models import Snapshot
from academic_workspace.source_map import build_source_map
import academic_workspace.cli as cli


class FakeTransport:
    def __init__(self, _profile):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class FakeCollector:
    def __init__(self, _transport):
        pass

    def collect(self):
        return Snapshot.from_mapping({"courses": [{"id": "c1", "name": "Curso"}], "activities": []})


def test_cli_skips_render_when_differential_check_is_clean(monkeypatch, capsys, tmp_path):
    snapshot = Snapshot.from_mapping({"courses": [{"id": "c1", "name": "Curso"}], "activities": []})
    source_map = build_source_map(snapshot)
    check = DifferentialCheck(source_map, {"added": 0, "changed": 0, "removed": 0}, True, True)
    monkeypatch.setattr(cli, "LiveBrowserTransport", FakeTransport)
    monkeypatch.setattr(cli, "BrowserApiCollector", FakeCollector)
    monkeypatch.setattr(cli, "check_differential", lambda _snapshot, _target, **_kwargs: check)
    monkeypatch.setattr(cli, "render_snapshot", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("no debe renderizar")))

    assert cli.main(["--target", str(tmp_path)]) == 0
    assert "sin descargas" in capsys.readouterr().out
    assert (tmp_path / ".blackboard-sync/generation-report.json").is_file()
    assert (tmp_path / ".blackboard-sync/execution-summary.json").is_file()
