from pathlib import Path
import json

from academic_workspace.providers.platzi import PlatziProvider


def test_platzi_provider_normalizes_courses_lessons_projects_and_progress(tmp_path: Path):
    source = tmp_path / "platzi.json"
    source.write_text(json.dumps({
        "courses": [{
            "id": "course-python",
            "code": "python",
            "name": "Python práctico",
            "url": "https://platzi.com/cursos/python/",
            "progress": 0.4,
            "lessons": [{"id": "lesson-1", "title": "Variables", "completed": True}],
            "projects": [{"id": "project-1", "title": "Proyecto final"}],
        }]
    }), encoding="utf-8")

    provider = PlatziProvider(source, instance="sample-instance")
    snapshot = provider.collect_snapshot()

    assert provider.provider_id == "platzi"
    assert provider.capabilities().content
    assert snapshot.courses[0].identity.key == "platzi:sample-instance:course-python"
    assert [item.title for item in snapshot.items] == ["Variables", "Proyecto final"]
    assert snapshot.items[0].metadata["completed"] is True
    assert snapshot.courses[0].metadata["progress"] == 0.4
