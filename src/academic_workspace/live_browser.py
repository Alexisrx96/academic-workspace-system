from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
import os
import shutil
import subprocess


class BlackboardSessionError(RuntimeError):
    pass


def _candidate_profile_dirs() -> tuple[Path, ...]:
    """Return profile locations without assuming a personal profile name."""
    candidates: list[Path] = []
    configured = os.environ.get("ACADEMIC_WORKSPACE_BROWSER_PROFILE")
    if configured:
        candidates.append(Path(configured))
    home = Path.home()
    roots = (
        home / "AppData/Local/CuaDriver/BrowserProfiles",
        home / "AppData/Local/Google/Chrome/User Data",
        home / "AppData/Local/BraveSoftware/Brave-Browser/User Data",
    )
    for root in roots:
        if root.is_dir():
            candidates.append(root)
            candidates.extend(sorted(path for path in root.iterdir() if path.is_dir()))
    seen: set[Path] = set()
    return tuple(path for path in candidates if not (path in seen or seen.add(path)))


def _chrome_executable() -> Path | None:
    candidates = (
        shutil.which("chrome.exe"),
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe"),
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return None


def launch_controlled_browser(profile_dir: Path | None = None) -> Path:
    """Launch a separate Chrome profile with DevTools enabled.

    The caller must still complete Blackboard authentication manually. This
    function never submits credentials and never replaces the user's browser.
    """
    executable = _chrome_executable()
    if executable is None:
        raise BlackboardSessionError("No se encontró chrome.exe para lanzar un navegador controlado.")
    profile = Path(profile_dir) if profile_dir else Path.home() / "AppData/Local/CuaDriver/BrowserProfiles/academic-workspace-live"
    profile.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [str(executable), "--remote-debugging-port=9222", f"--user-data-dir={profile}", "https://utecvirtual.blackboard.com/"],
        close_fds=True,
    )
    return profile


class LiveBrowserTransport:
    """Read-only API transport through any active Blackboard browser session.

    It discovers DevTools endpoints instead of assuming a profile name, then
    selects the first endpoint whose browser context is authenticated to the
    configured Blackboard host. It never submits login forms or receives
    user/password/API credentials.
    """

    def __init__(self, profile_dir: Path | None = None):
        self.profile_dir = Path(profile_dir) if profile_dir else None
        self._playwright = None
        self._browser = None
        self._request = None

    def _profiles(self) -> tuple[Path, ...]:
        return (self.profile_dir,) if self.profile_dir else _candidate_profile_dirs()

    def __enter__(self) -> "LiveBrowserTransport":
        try:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
        except Exception as error:
            raise BlackboardSessionError("No se pudo iniciar el cliente del navegador.") from error

        attempted: list[str] = []
        for profile in self._profiles():
            port_file = profile / "DevToolsActivePort"
            try:
                port = port_file.read_text(encoding="utf-8").splitlines()[0].strip()
            except (OSError, IndexError):
                continue
            attempted.append(str(profile))
            try:
                browser = self._playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                if not browser.contexts:
                    continue
                request = browser.contexts[0].request
                response = request.get("https://utecvirtual.blackboard.com/learn/api/v1/users/me")
                if not response.ok:
                    continue
                self.profile_dir = profile
                self._browser = browser
                self._request = request
                return self
            except Exception:
                continue
        self._playwright.stop()
        self._playwright = None
        scope = str(self.profile_dir) if self.profile_dir else "los perfiles de navegador detectados"
        raise BlackboardSessionError(
            f"No se encontró una sesión DevTools autenticada en Blackboard en {scope}. "
            "La sesión debe exponer DevTools; no se requiere un nombre de perfil específico."
        )

    def __exit__(self, *_: object) -> None:
        # Do not close the user-owned browser or stop its process.
        self._playwright = self._browser = self._request = None

    def get_json(self, path: str) -> Mapping[str, Any]:
        if self._request is None:
            raise BlackboardSessionError("El transporte no está abierto.")
        url = "https://utecvirtual.blackboard.com" + path
        try:
            response = self._request.get(url)
            if not response.ok:
                raise BlackboardSessionError(f"Blackboard devolvió HTTP {response.status} para {path}")
            payload = response.json()
        except BlackboardSessionError:
            raise
        except Exception as error:
            raise BlackboardSessionError(f"No se pudo leer {path}") from error
        if not isinstance(payload, Mapping):
            raise BlackboardSessionError(f"Respuesta JSON no compatible para {path}")
        return payload

    def fetch_rendered_html(self, source_url: str) -> str:
        """Read rendered HTML in the already connected browser session."""
        if self._browser is None or not self._browser.contexts:
            raise BlackboardSessionError("El transporte no está abierto.")
        try:
            page = self._browser.contexts[0].new_page()
            page.goto(source_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
            html = page.content()
            page.close()
            return html
        except Exception as error:
            raise BlackboardSessionError("No se pudo leer el HTML renderizado del recurso externo.") from error

    def fetch(self, source_url: str) -> bytes:
        """Download a Blackboard-hosted file using the browser's session cookie."""
        if self._request is None:
            raise BlackboardSessionError("El transporte no está abierto.")
        parsed = urlsplit(source_url)
        if parsed.netloc and parsed.netloc != "utecvirtual.blackboard.com":
            raise BlackboardSessionError("Solo se pueden descargar adjuntos del dominio Blackboard UTEC.")
        if not parsed.path.startswith("/bbcswebdav/"):
            raise BlackboardSessionError("La URL del adjunto no corresponde a un recurso Blackboard observado.")
        url = "https://utecvirtual.blackboard.com" + parsed.path
        if parsed.query:
            url += "?" + parsed.query
        try:
            response = self._request.get(url)
            if not response.ok:
                raise BlackboardSessionError(f"Blackboard devolvió HTTP {response.status} al descargar un adjunto.")
            return response.body()
        except BlackboardSessionError:
            raise
        except Exception as error:
            raise BlackboardSessionError("No se pudo descargar un adjunto de Blackboard.") from error
