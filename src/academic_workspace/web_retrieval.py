from __future__ import annotations

from hashlib import sha256
import html
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import quote_plus, urlsplit
from urllib.request import Request, urlopen

from .companion_contracts import ExternalSourceRecord
from .source_validation import stable_source_id, validate_external_source

_MAX_BYTES = 2 * 1024 * 1024
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def html_to_text(document: str) -> tuple[str, str]:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", document, re.IGNORECASE | re.DOTALL)
    title = _SPACE_RE.sub(" ", html.unescape(title_match.group(1))).strip() if title_match else ""
    cleaned = re.sub(r"<(script|style|noscript|title)[^>]*>.*?</\1>", " ", document, flags=re.IGNORECASE | re.DOTALL)
    text = html.unescape(_TAG_RE.sub(" ", cleaned))
    return title, _SPACE_RE.sub(" ", text).strip()


def _read_response(opener: Callable[..., object], request: Request) -> bytes:
    response = opener(request, timeout=20)
    try:
        return response.read(_MAX_BYTES) if hasattr(response, "read") else bytes(response)
    finally:
        close = getattr(response, "close", None)
        if callable(close):
            close()


def fetch_external_source(
    url: str,
    *,
    purpose: str,
    authorized: bool,
    retrieved_at: str | None = None,
    quotes: tuple[str, ...] = (),
    artifact_root: Path | None = None,
    opener: Callable[..., object] = urlopen,
) -> ExternalSourceRecord:
    if not authorized:
        raise PermissionError("la recuperación web requiere autorización explícita")
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("solo se permiten URLs http/https")
    payload = _read_response(opener, Request(url, headers={"User-Agent": "academic-workspace/1.0"}))
    content_hash = sha256(payload).hexdigest()
    document = payload.decode("utf-8", errors="replace")
    title, text = html_to_text(document)
    timestamp = retrieved_at or datetime.now(timezone.utc).isoformat()
    snapshot_path = ""
    if artifact_root is not None:
        relative = Path(".blackboard-sync") / "external-sources" / f"{content_hash}.txt"
        snapshot = Path(artifact_root) / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_text(f"{title or url}\n\n{text}\n", encoding="utf-8", newline="\n")
        snapshot_path = relative.as_posix()
    source = ExternalSourceRecord(
        source_id=stable_source_id(url, content_hash),
        url=url,
        title=title or url,
        source_type="web",
        publisher=parsed.netloc,
        retrieved_at=timestamp,
        content_hash=content_hash,
        purpose=purpose,
        authorized=True,
        snapshot_path=snapshot_path,
        evidence=tuple({"quote": quote, "text": text} for quote in quotes),
    )
    validate_external_source(source)
    return source


def search_web(
    query: str,
    *,
    authorized: bool,
    opener: Callable[..., object] = urlopen,
) -> list[dict[str, str]]:
    if not authorized:
        raise PermissionError("la búsqueda web requiere autorización explícita")
    if not query.strip():
        raise ValueError("query no puede estar vacío")
    endpoint = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
    payload = _read_response(opener, Request(endpoint, headers={"User-Agent": "academic-workspace/1.0"}))
    document = payload.decode("utf-8", errors="replace")
    pattern = re.compile(r'<a[^>]+class=["\']result__a["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
    hits: list[dict[str, str]] = []
    seen: set[str] = set()
    for url, raw_title in pattern.findall(document):
        url = html.unescape(url)
        title = _SPACE_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", raw_title))).strip()
        if url.startswith("//"):
            url = "https:" + url
        if url.startswith("http") and url not in seen:
            seen.add(url)
            hits.append({"title": title, "url": url})
    return hits
