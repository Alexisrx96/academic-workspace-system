from academic_workspace.models import Snapshot
from academic_workspace.source_map import build_source_map, diff_source_maps


def test_source_map_is_stable_and_excludes_browser_resource_urls():
    snapshot = Snapshot.from_mapping({
        "courses": [{"id": "c1", "course_id": "ELE1", "name": "Electrónica"}],
        "activities": [{
            "id": "folder-1", "course_id": "c1", "kind": "content", "title": "Semana 1", "is_container": True,
            "attachments": [{"id": "a1", "name": "guia.pdf", "mime_type": "application/pdf", "size": 10, "source_url": "/bbcswebdav/secret"}],
        }],
    })

    source_map = build_source_map(snapshot)

    assert source_map.payload["items"][0]["note_path"] == "Blackboard/ELE1/Contenido/Semana 1--folder-1/index.md"
    assert source_map.payload["items"][0]["attachments"][0]["path"] == "Blackboard/ELE1/Contenido/Semana 1--folder-1/Adjuntos/guia--a1.pdf"
    assert "bbcswebdav" not in source_map.content
    assert diff_source_maps(source_map, source_map) == {"added": 0, "changed": 0, "removed": 0}


def test_source_map_identifies_changed_blackboard_item():
    before = build_source_map(Snapshot.from_mapping({
        "courses": [{"id": "c1", "name": "Curso"}],
        "activities": [{"id": "x1", "course_id": "c1", "kind": "content", "title": "Antes"}],
    }))
    after = build_source_map(Snapshot.from_mapping({
        "courses": [{"id": "c1", "name": "Curso"}],
        "activities": [{"id": "x1", "course_id": "c1", "kind": "content", "title": "Después"}],
    }))

    assert diff_source_maps(after, before) == {"added": 0, "changed": 1, "removed": 0}
