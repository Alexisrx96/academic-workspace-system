import json
from pathlib import Path

import pytest

from academic_workspace.companion_contracts import (
    ExternalSourceRecord,
    ValidationRecord,
)
from academic_workspace.companion_kernel import (
    record_external_source,
    record_validation,
    study_policy,
)
from academic_workspace.workspace_commands import default_config, init_workspace


def test_policy_defaults_to_guided_and_ask_first(tmp_path: Path):
    policy = study_policy(tmp_path)

    assert policy.mode == "guided"
    assert policy.external_lookup == "ask_first"
    assert policy.source_policy == "course_first"


def test_external_source_and_validation_are_append_once(tmp_path: Path):
    source = ExternalSourceRecord(
        source_id="external-source:x",
        url="https://example.org/page",
        title="Page",
        source_type="university",
        publisher="University",
        retrieved_at="2026-08-22T12:00:00Z",
        content_hash="a" * 64,
        purpose="cross_check",
        authorized=True,
        evidence=({"quote": "Exact", "text": "Exact text"},),
    )
    validation = ValidationRecord("A", "A", "externally_confirmed", ("course", source.source_id), ("Exact",))

    first = record_external_source(tmp_path, source)
    second = record_external_source(tmp_path, source)
    record_validation(tmp_path, validation)

    lines = (tmp_path / ".blackboard-sync/evidence.jsonl").read_text(encoding="utf-8").splitlines()
    assert first == second
    assert len(lines) == 2
    assert json.loads(lines[0])["schema"] == "external-source.v1"


def test_external_source_policy_is_enforced_before_persistence(tmp_path: Path):
    init_workspace(tmp_path)
    config = default_config().to_dict()
    config["privacy"]["allow_external_sources"] = False
    (tmp_path / ".blackboard-sync" / "workspace-config.json").write_text(json.dumps(config), encoding="utf-8")
    source = ExternalSourceRecord(
        source_id="external-source:x",
        url="https://example.org/page",
        title="Page",
        source_type="web",
        publisher="Example",
        retrieved_at="2026-08-22T12:00:00Z",
        content_hash="a" * 64,
        purpose="cross_check",
        authorized=True,
    )

    with pytest.raises(PermissionError, match="fuentes externas"):
        record_external_source(tmp_path, source)
