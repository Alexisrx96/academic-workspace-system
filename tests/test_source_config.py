import json
from pathlib import Path

import pytest

from academic_workspace.source_config import (
    SourceConfig,
    SourceConfigError,
    load_source_configs,
    register_source,
)


def test_source_config_defaults_to_legacy_blackboard_lane(tmp_path: Path):
    configs = load_source_configs(tmp_path)

    assert configs == (SourceConfig(provider="blackboard_ultra", instance="default", root="Blackboard"),)


def test_source_config_loads_multiple_sources_and_rejects_invalid_entries(tmp_path: Path):
    path = tmp_path / ".blackboard-sync" / "sources.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "format": 1,
        "sources": [
            {"provider": "fixture", "instance": "demo", "root": "Fuentes/Fixture"},
            {"provider": "blackboard_ultra", "instance": "utec", "root": "Blackboard"},
        ],
    }), encoding="utf-8")

    configs = load_source_configs(tmp_path)

    assert configs == (
        SourceConfig(provider="fixture", instance="demo", root="Fuentes/Fixture"),
        SourceConfig(provider="blackboard_ultra", instance="utec", root="Blackboard"),
    )


def test_source_config_rejects_malformed_file(tmp_path: Path):
    path = tmp_path / ".blackboard-sync" / "sources.json"
    path.parent.mkdir(parents=True)
    path.write_text("not-json", encoding="utf-8")

    with pytest.raises(SourceConfigError, match="sources.json"):
        load_source_configs(tmp_path)


def test_source_config_rejects_root_outside_workspace(tmp_path: Path):
    path = tmp_path / ".blackboard-sync" / "sources.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "format": 1,
        "sources": [{"provider": "fixture", "instance": "demo", "root": "../escape"}],
    }), encoding="utf-8")

    with pytest.raises(SourceConfigError, match="fuera del workspace"):
        load_source_configs(tmp_path)

    with pytest.raises(SourceConfigError, match="fuera del workspace"):
        register_source(tmp_path, "fixture", "demo", "../escape")


def test_source_config_rejects_parent_segments_even_when_they_resolve_inside(tmp_path: Path):
    path = tmp_path / ".blackboard-sync" / "sources.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "format": 1,
        "sources": [{"provider": "fixture", "instance": "demo", "root": "Foo/../Bar"}],
    }), encoding="utf-8")

    with pytest.raises(SourceConfigError, match="segmentos"):
        load_source_configs(tmp_path)
