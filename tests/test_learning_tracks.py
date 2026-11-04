import json
from pathlib import Path

from academic_workspace.learning_tracks import list_tracks, register_track


def test_learning_track_supports_non_institutional_goals(tmp_path: Path):
    track = register_track(tmp_path, "python-advanced", "Python avanzado", "programming", ["Diseñar APIs", "Escribir tests"], ["Fuentes/Autodidacta/Python-Advanced"])
    tracks = list_tracks(tmp_path)

    assert track["schema"] == "learning-track.v1"
    assert track["kind"] == "programming"
    assert tracks[0]["objectives"] == ["Diseñar APIs", "Escribir tests"]
