from datetime import datetime, timezone
from pathlib import Path

from academic_workspace.providers.contracts import (
    AcademicSourceProvider,
    SourceCapabilities,
    SourceHealth,
    SourceIdentity,
)
from academic_workspace.providers.fixture import FixtureProvider
from academic_workspace.providers.blackboard_ultra import BlackboardUltraProvider
from academic_workspace.providers.registry import get_provider, register_provider
from academic_workspace.models import Activity, Course, Snapshot


def test_source_identity_is_stable_across_platforms():
    blackboard = SourceIdentity("blackboard_ultra", "utec", "course-1")
    moodle = SourceIdentity("moodle", "utec", "course-1")

    assert blackboard.key == "blackboard_ultra:utec:course-1"
    assert blackboard.key != moodle.key


def test_fixture_provider_satisfies_source_provider_contract(tmp_path: Path):
    fixture = tmp_path / "source.json"
    fixture.write_text(
        '{"courses": [{"id": "c1", "code": "SINF", "name": "Sistemas"}], '
        '"items": [{"id": "i1", "course_id": "c1", "kind": "assignment", '
        '"title": "Tarea", "due_at": "2026-08-20T23:59:00Z"}]}',
        encoding="utf-8",
    )
    provider: AcademicSourceProvider = FixtureProvider(fixture, instance="test")

    snapshot = provider.collect_snapshot()

    assert provider.provider_id == "fixture"
    assert provider.instance_id == "test"
    assert provider.capabilities().assignments
    assert snapshot.courses[0].identity == SourceIdentity("fixture", "test", "c1")
    assert snapshot.items[0].identity.key == "fixture:test:i1"
    assert snapshot.items[0].due_at == datetime(2026, 8, 20, 23, 59, tzinfo=timezone.utc)
    assert provider.health().status == "verified"


def test_provider_registry_is_explicit_and_replaceable():
    register_provider("fixture-test", lambda: "first")
    register_provider("fixture-test", lambda: "second")

    assert get_provider("fixture-test")() == "second"


def test_blackboard_ultra_adapter_normalizes_legacy_snapshot():
    legacy = Snapshot(
        courses=(Course(id="c1", name="Sistemas", course_id="SINF"),),
        activities=(Activity(id="a1", course_id="c1", kind="assignment", title="Tarea", due_at="2026-08-20T23:59:00Z"),),
    )
    provider = BlackboardUltraProvider(lambda: legacy, instance="utec")

    snapshot = provider.collect_snapshot()

    assert snapshot.provider == "blackboard_ultra"
    assert snapshot.courses[0].identity.key == "blackboard_ultra:utec:c1"
    assert snapshot.items[0].identity.key == "blackboard_ultra:utec:a1"
    assert snapshot.items[0].course.external_id == "c1"
    assert provider.health().status == "unknown"


def test_blackboard_ultra_adapter_reports_collection_failure():
    provider = BlackboardUltraProvider(lambda: (_ for _ in ()).throw(RuntimeError("sesión cerrada")))

    try:
        provider.collect_snapshot()
    except RuntimeError:
        pass
    else:
        raise AssertionError("se esperaba que el adaptador propagara el error")

    assert provider.health().status == "unavailable"
    assert "sesión cerrada" in (provider.health().message or "")
