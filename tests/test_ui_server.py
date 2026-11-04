from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from academic_workspace.application import AcademicWorkspaceKernel
from ui.server import Handler


@contextmanager
def running_server(target: Path):
    Handler.target = target.resolve()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def get_json(url: str, *, origin: str | None = None):
    headers = {"Origin": origin} if origin else {}
    with urlopen(Request(url, headers=headers), timeout=5) as response:
        return response.status, dict(response.headers), json.loads(response.read())


def post_json(url: str, payload: dict, *, content_type: str = "application/json", origin: str | None = None):
    headers = {"Content-Type": content_type}
    if origin:
        headers["Origin"] = origin
    request = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urlopen(request, timeout=5) as response:
        return response.status, dict(response.headers), json.loads(response.read())


def test_ui_rejects_cross_origin_reads(tmp_path: Path):
    with running_server(tmp_path) as base:
        try:
            get_json(base + "/api/workspace", origin="https://evil.example")
        except HTTPError as error:
            assert error.code == 403
            assert error.headers.get("Access-Control-Allow-Origin") is None
        else:
            raise AssertionError("la UI debía rechazar el origen externo")


def test_ui_requires_json_for_state_changing_requests(tmp_path: Path):
    note = tmp_path / "02 - Cursos" / "TEST" / "nota.md"
    note.parent.mkdir(parents=True)
    note.write_text("original\n", encoding="utf-8")
    with running_server(tmp_path) as base:
        try:
            post_json(
                base + "/api/source/save",
                {"path": "02 - Cursos/TEST/nota.md", "content": "modificado\n"},
                content_type="text/plain",
            )
        except HTTPError as error:
            assert error.code == 415
        else:
            raise AssertionError("la UI debía exigir application/json")
    assert note.read_text(encoding="utf-8") == "original\n"


def test_ui_sanitizes_rendered_markdown_html(tmp_path: Path):
    note = tmp_path / "Blackboard" / "TEST" / "fuente.md"
    note.parent.mkdir(parents=True)
    note.write_text('<img src="x" onerror="alert(1)"><script>alert(2)</script>\n', encoding="utf-8")
    with running_server(tmp_path) as base:
        _, _, payload = get_json(base + "/api/source?path=Blackboard/TEST/fuente.md")

    assert "onerror" not in payload["html"]
    assert "<script" not in payload["html"]


def test_ui_exposes_persisted_session_list_and_detail(tmp_path: Path):
    kernel = AcademicWorkspaceKernel(tmp_path)
    session = kernel.start_study_session("FIS1", "Cinemática", "Comprender")

    with running_server(tmp_path) as base:
        _, _, listed = get_json(base + "/api/sessions")
        _, _, detail = get_json(base + f"/api/session?session_id={session.session_id}")

    assert listed["schema"] == "study-session-list.v1"
    assert [item["session_id"] for item in listed["sessions"]] == [session.session_id]
    assert detail["session_id"] == session.session_id


def test_ui_can_pause_and_resume_a_persisted_session(tmp_path: Path):
    session = AcademicWorkspaceKernel(tmp_path).start_study_session("FIS1", "Cinemática", "Comprender")

    with running_server(tmp_path) as base:
        _, _, paused = post_json(base + "/api/session/transition", {"session_id": session.session_id, "status": "paused"})
        _, _, resumed = post_json(base + "/api/session/transition", {"session_id": session.session_id, "status": "active"})
        _, _, detail = get_json(base + f"/api/session?session_id={session.session_id}")

    assert paused["status"] == "paused"
    assert resumed["status"] == "active"
    assert detail["status"] == "active"


def test_ui_uses_configured_source_root_and_opens_course_index(tmp_path: Path):
    state = tmp_path / ".blackboard-sync"
    state.mkdir()
    (state / "sources.json").write_text(json.dumps({
        "format": 1,
        "sources": [{"provider": "fixture", "instance": "demo", "root": "Fuentes/Fixture"}],
    }), encoding="utf-8")
    (tmp_path / "02 - Cursos" / "TEST").mkdir(parents=True)
    official = tmp_path / "Fuentes" / "Fixture" / "TEST-COURSE"
    official.mkdir(parents=True)
    (official / "index.md").write_text("# Curso TEST\n", encoding="utf-8")
    control = tmp_path / "Control Académico"
    control.mkdir()
    (control / "Matriz de dominio.md").write_text("| Curso | Bloque |\n|---|---|\n", encoding="utf-8")

    with running_server(tmp_path) as base:
        _, _, workspace = get_json(base + "/api/workspace")
        _, _, course = get_json(base + "/api/course?code=TEST")

    assert workspace["source_root_exists"] is True
    assert course["official"][0]["path"] == "Fuentes/Fixture/TEST-COURSE/index.md"
