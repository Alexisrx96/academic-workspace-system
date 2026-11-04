from __future__ import annotations

import sys
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.parse import quote

from playwright.sync_api import sync_playwright

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


def main() -> int:
    with TemporaryDirectory() as raw:
        target = Path(raw)
        kernel = AcademicWorkspaceKernel(target)
        session = kernel.start_study_session("FIS1", "Cinemática", "Comprender")
        blocked_session = kernel.start_study_session("FIS1", "Dinámica", "Comprender")
        kernel.transition_study_session(blocked_session.session_id, "blocked")
        with running_server(target) as base, sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page()
            console_errors = []
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            page.goto(base + f"/#/session/{session.session_id}", wait_until="networkidle")
            body = page.locator("body").inner_text()
            assert "FIS1 · Cinemática" in body, body
            assert "No se pudo cargar esta vista" not in body, body
            page.get_by_role("button", name="Pausar sesión").click()
            page.get_by_role("button", name="Reanudar sesión").wait_for()
            page.reload(wait_until="networkidle")
            page.get_by_role("button", name="Reanudar sesión").wait_for()
            page.get_by_role("button", name="Reanudar sesión").click()
            page.get_by_role("button", name="Pausar sesión").wait_for()
            page.goto(base + "/#/hoy", wait_until="networkidle")
            page.get_by_text("Continuar sesión →", exact=True).first.wait_for()
            body = page.locator("body").inner_text()
            assert "Continuar sesión" in body, body
            kernel.start_study_session("FIS1", "Ondas", "Comprender")
            page.goto(base + "/#/metrics", wait_until="networkidle")
            page.get_by_text("Métricas de estudio", exact=True).wait_for()
            page.get_by_role("button", name="Hoy").click()
            page.get_by_text("FIS1 · Ondas", exact=True).wait_for()
            page.goto(base + f"/#/session/{blocked_session.session_id}", wait_until="networkidle")
            page.get_by_role("button", name="Reanudar sesión").wait_for()
            malicious = quote('<img id="pwn" src="x">', safe="")
            page.goto(base + f"/#/session/{malicious}", wait_until="networkidle")
            page.get_by_text("No se pudo cargar esta vista", exact=True).wait_for()
            assert page.locator("#pwn").count() == 0
            assert not [error for error in console_errors if "Content Security Policy" in error], console_errors
            browser.close()
    print("browser session continuity smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
