from __future__ import annotations

import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import bleach
import markdown

from academic_workspace.application import AcademicWorkspaceKernel
from academic_workspace.next_study_action import next_study_action
from academic_workspace.note_editor import save_user_note
from academic_workspace.source_config import load_source_configs
from academic_workspace.spaced_review import schedule_review
from academic_workspace.study_metrics import build_study_metrics
from academic_workspace.study_preflight import build_preflight
from academic_workspace.study_sessions import create_attempt

_ALLOWED_HTML_TAGS = {
    "a", "blockquote", "br", "code", "del", "em", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "img", "li", "ol", "p", "pre", "strong", "table", "tbody", "td", "th", "thead", "tr", "ul",
}
_ALLOWED_HTML_ATTRIBUTES = {
    "a": ["href", "title"],
    "img": ["src", "alt", "title"],
    "code": ["class"],
}


class Handler(BaseHTTPRequestHandler):
    target: Path

    def log_message(self, format, *args):
        return

    def security_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")

    def request_allowed(self) -> bool:
        host = self.headers.get("Host", "")
        port = self.server.server_port
        allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if host not in allowed_hosts:
            return False
        origin = self.headers.get("Origin")
        return origin is None or origin in {f"http://{item}" for item in allowed_hosts}

    def send_json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.security_headers()
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        parsed = urlparse(self.path)
        try:
            if not self.request_allowed():
                self.send_json(403, {"error": "origen no permitido"}); return
            if parsed.path == "/":
                data = (Path(__file__).parent / "index.html").read_bytes()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.security_headers(); self.end_headers(); self.wfile.write(data); return
            if parsed.path.startswith("/static/"):
                relative = parsed.path.removeprefix("/static/")
                asset = (Path(__file__).parent / relative).resolve()
                ui_root = Path(__file__).parent.resolve()
                if ui_root not in asset.parents or not asset.is_file():
                    self.send_json(404, {"error": "asset not found"}); return
                data = asset.read_bytes()
                content_type = "text/css; charset=utf-8" if asset.suffix == ".css" else "text/javascript; charset=utf-8"
                self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(data))); self.security_headers(); self.end_headers(); self.wfile.write(data); return
            if parsed.path == "/api/metrics":
                self.send_json(200, build_study_metrics(self.target)); return
            if parsed.path == "/api/workspace":
                courses_root = self.target / "02 - Cursos"
                courses = []
                if courses_root.is_dir():
                    for course in sorted(p for p in courses_root.iterdir() if p.is_dir()):
                        courses.append({"code": course.name, "notes": sum(1 for p in course.rglob("*.md")), "path": course.relative_to(self.target).as_posix()})
                dashboard_path = self.target / "Control Académico/00 - Dashboard académico.md"
                dashboard_text = dashboard_path.read_text(encoding="utf-8", errors="replace") if dashboard_path.is_file() else ""
                attention = []
                for line in dashboard_text.splitlines():
                    if not line.startswith("- [ ]"):
                        continue
                    raw = line[6:].strip()
                    match = re.search(r"\[([^\]]+)\]\(([^)]+)\)", raw)
                    source_path = ""
                    title = raw
                    if match:
                        title = raw.replace(match.group(0), match.group(1)).replace("**", "")
                        candidate = (dashboard_path.parent / match.group(2)).resolve()
                        if self.target.resolve() in candidate.parents and candidate.is_file():
                            source_path = candidate.relative_to(self.target.resolve()).as_posix()
                    course = title.rsplit("—", 1)[-1].strip() if "—" in title else ""
                    attention.append({"title": title, "course": course, "source_path": source_path})
                matrix_path = self.target / "Control Académico/Matriz de dominio.md"
                matrix_text = matrix_path.read_text(encoding="utf-8", errors="replace") if matrix_path.is_file() else ""
                domain = []
                for line in matrix_text.splitlines():
                    if not line.startswith("|") or "---" in line or "Curso |" in line:
                        continue
                    cells = [cell.strip() for cell in line.strip("|").split("|")]
                    if len(cells) >= 2:
                        domain.append({"course": cells[0], "topic": cells[1], "explanation": cells[2] if len(cells)>2 else "—", "application": cells[3] if len(cells)>3 else "—", "next_action": cells[5] if len(cells)>5 else "—"})
                source_roots = [self.target / source.root for source in load_source_configs(self.target)]
                sessions = [item.to_dict() for item in AcademicWorkspaceKernel(self.target).study_sessions() if item.status in {"active", "paused", "blocked"}]
                self.send_json(200, {"schema": "study-workspace.v1", "target": self.target.as_posix(), "courses": courses, "source_root_exists": any(root.is_dir() for root in source_roots), "dashboard": dashboard_path.is_file(), "weekly_state": (self.target / "Control Académico/Estado semanal.md").is_file(), "attention": attention[:10], "domain": domain[:30], "sessions": sessions}); return
            if parsed.path == "/api/sessions":
                status = parse_qs(parsed.query).get("status", [None])[0]
                sessions = AcademicWorkspaceKernel(self.target).study_sessions(status=status)
                self.send_json(200, {"schema": "study-session-list.v1", "sessions": [item.to_dict() for item in sessions]}); return
            if parsed.path == "/api/session":
                session_id = parse_qs(parsed.query).get("session_id", [""])[0]
                self.send_json(200, AcademicWorkspaceKernel(self.target).study_session(session_id).to_dict()); return
            if parsed.path == "/api/course":
                code = parse_qs(parsed.query).get("code", [""])[0]
                work = self.target / "02 - Cursos" / code
                if not work.is_dir():
                    self.send_json(404, {"error": "curso no encontrado"}); return
                own_notes = [{"title": p.stem, "path": p.relative_to(self.target).as_posix()} for p in sorted(work.rglob("*.md")) if p.is_file()][:100]
                official = []
                for source in load_source_configs(self.target):
                    official_root = self.target / source.root
                    if not official_root.is_dir():
                        continue
                    for folder in sorted(p for p in official_root.iterdir() if p.is_dir() and p.name.startswith(code)):
                        index = folder / "index.md"
                        destination = index if index.is_file() else folder
                        official.append({"title": folder.name, "path": destination.relative_to(self.target).as_posix(), "notes": sum(1 for p in folder.rglob("*.md") if p.is_file())})
                matrix = []
                for item in self.target.joinpath("Control Académico/Matriz de dominio.md").read_text(encoding="utf-8", errors="replace").splitlines():
                    if item.startswith("|") and "---" not in item and "Curso |" not in item:
                        cells = [x.strip() for x in item.strip("|").split("|")]
                        if len(cells) >= 2 and cells[0] == code:
                            matrix.append({"topic": cells[1], "explanation": cells[2], "application": cells[3]})
                self.send_json(200, {"schema": "study-course.v1", "code": code, "own_notes": own_notes, "official": official, "topics": matrix}); return
            if parsed.path == "/api/asset":
                requested = parse_qs(parsed.query).get("path", [""])[0]
                asset = (self.target / requested).resolve()
                if self.target.resolve() not in asset.parents or not asset.is_file():
                    self.send_json(404, {"error": "recurso no encontrado"}); return
                content_types={".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".gif":"image/gif",".svg":"image/svg+xml",".webp":"image/webp",".pdf":"application/pdf"}
                data=asset.read_bytes(); self.send_response(200); self.send_header("Content-Type",content_types.get(asset.suffix.lower(),"application/octet-stream")); self.send_header("Content-Length",str(len(data))); self.security_headers(); self.end_headers(); self.wfile.write(data); return
            if parsed.path == "/api/source":
                requested = parse_qs(parsed.query).get("path", [""])[0]
                candidate = (self.target / requested).resolve()
                if self.target.resolve() not in candidate.parents or not candidate.is_file():
                    self.send_json(404, {"error": "fuente no encontrada"}); return
                content = candidate.read_text(encoding="utf-8", errors="replace")
                content_for_md = re.sub(r"!\[\[([^\]]+)\]\]", lambda match: f'<img src="/api/asset?path={quote((candidate.parent / match.group(1)).resolve().relative_to(self.target.resolve()).as_posix())}" alt="{match.group(1)}">' if (candidate.parent / match.group(1)).resolve().is_file() and self.target.resolve() in (candidate.parent / match.group(1)).resolve().parents else match.group(0), content)
                rendered = markdown.markdown(content_for_md, extensions=["fenced_code", "tables", "footnotes"])
                base_dir = candidate.parent
                def asset_src(match):
                    source = match.group(1)
                    if source.startswith(("http://", "https://", "data:")):
                        return match.group(0)
                    asset = (base_dir / source).resolve()
                    if self.target.resolve() not in asset.parents or not asset.is_file():
                        return match.group(0)
                    relative = asset.relative_to(self.target.resolve()).as_posix()
                    return f'src="/api/asset?path={quote(relative)}"'
                rendered = re.sub(r'src="([^"]+)"', asset_src, rendered)
                rendered = bleach.clean(rendered, tags=_ALLOWED_HTML_TAGS, attributes=_ALLOWED_HTML_ATTRIBUTES, protocols={"http", "https", "data"}, strip=True)
                self.send_json(200, {"schema": "study-source.v1", "path": candidate.relative_to(self.target.resolve()).as_posix(), "title": candidate.stem, "content": content, "html": rendered, "editable": candidate.relative_to(self.target.resolve()).as_posix().startswith("02 - Cursos/")}); return
            if parsed.path == "/api/preflight":
                session_id = parse_qs(parsed.query).get("session_id", [""])[0]
                session = AcademicWorkspaceKernel(self.target).study_session(session_id).to_dict()
                self.send_json(200, build_preflight(self.target, session)); return
            self.send_json(404, {"error": "not found"})
        except (KeyError, OSError, PermissionError, TypeError, ValueError) as exc:
            self.send_json(400, {"error": str(exc)})
        except Exception:  # noqa: BLE001 - isolate unexpected failures at the HTTP boundary
            self.send_json(500, {"error": "error interno del panel"})

    def do_POST(self):
        try:
            if not self.request_allowed():
                self.send_json(403, {"error": "origen no permitido"}); return
            if self.headers.get_content_type() != "application/json":
                length = int(self.headers.get("Content-Length", "0"))
                if length:
                    self.rfile.read(length)
                self.send_json(415, {"error": "Content-Type debe ser application/json"}); return
            payload = self.read_json()
            kernel = AcademicWorkspaceKernel(self.target)
            if self.path == "/api/source/save":
                path = save_user_note(self.target, payload["path"], payload["content"])
                result = {"schema": "study-source-save.v1", "path": path.relative_to(self.target.resolve()).as_posix(), "saved": True}
            elif self.path == "/api/session/start":
                result = kernel.start_study_session(payload["course"], payload["topic"], payload["objective"], payload.get("mode", "guided"), tuple(payload.get("source_refs", ())), int(payload.get("minutes", 25))).to_dict()
            elif self.path == "/api/session/attempt":
                session = kernel.study_session(payload["session_id"])
                attempt = create_attempt(session, payload["phase"], payload["response"], payload.get("feedback", ""), payload["result"], tuple(payload.get("error_tags", ())), confidence=payload.get("confidence"), help_level=int(payload.get("help_level", 0)))
                event_id = kernel.record_study_attempt(attempt)
                review = schedule_review(payload["result"], payload.get("confidence")); review.update({"session_id": session.session_id, "attempt_id": attempt.attempt_id}); review["event_id"] = kernel.record_study_review(review)
                result = {**attempt.to_dict(), "event_id": event_id, "next_action": next_study_action(payload["result"], tuple(payload.get("error_tags", ())), payload.get("confidence")), "review": review}
            elif self.path == "/api/session/transition":
                result = kernel.transition_study_session(payload["session_id"], payload["status"]).to_dict()
            elif self.path == "/api/session/complete":
                result = kernel.transition_study_session(payload["session_id"], "completed").to_dict()
            else:
                self.send_json(404, {"error": "not found"}); return
            self.send_json(200, result)
        except (KeyError, OSError, PermissionError, TypeError, ValueError) as exc:
            self.send_json(400, {"error": str(exc)})
        except Exception:  # noqa: BLE001 - isolate unexpected failures at the HTTP boundary
            self.send_json(500, {"error": "error interno del panel"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    Handler.target = args.target.resolve()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"study-panel http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
