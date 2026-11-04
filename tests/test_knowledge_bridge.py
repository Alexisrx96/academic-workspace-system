import json
from pathlib import Path

from academic_workspace.knowledge_bridge import refresh_knowledge_bridge


def test_knowledge_bridge_links_blackboard_to_existing_root_notes_without_changing_them(tmp_path: Path):
    source_map = {
        "format": 2,
        "output_format": 2,
        "courses": [
            {"id": "c1", "course_code": "SINF-V02-022026", "path": "Blackboard/SINF-V02-022026"},
            {"id": "c2", "course_code": "ADCC-V02-022026", "path": "Blackboard/ADCC-V02-022026"},
        ],
        "items": [],
    }
    (tmp_path / ".blackboard-sync").mkdir()
    (tmp_path / ".blackboard-sync" / "source-map.json").write_text(json.dumps(source_map), encoding="utf-8")
    personal = tmp_path / "SINF" / "Tarea 1.md"
    personal.parent.mkdir()
    personal.write_text("# Mi trabajo\n\nContenido propio.\n", encoding="utf-8")

    result = refresh_knowledge_bridge(tmp_path)

    hub = tmp_path / "SINF" / "00 - Blackboard y apuntes.md"
    assert result.course_count == 2
    assert hub.is_file()
    assert "[[Blackboard/SINF-V02-022026/index|Fuente académica: SINF-V02-022026]]" in hub.read_text(encoding="utf-8")
    assert "[[SINF/Tarea 1|Tarea 1]]" in hub.read_text(encoding="utf-8")
    assert personal.read_text(encoding="utf-8") == "# Mi trabajo\n\nContenido propio.\n"
    assert (tmp_path / "02 - Cursos" / "ADCC" / "00 - Blackboard y apuntes.md").is_file()
    config = json.loads((tmp_path / "Control Académico" / "Mapa de cursos.json").read_text(encoding="utf-8"))
    assert config["courses"]["SINF-V02-022026"]["workspace"] == "SINF"
    assert (tmp_path / "Control Académico" / "Mapa de conocimiento.md").is_file()
