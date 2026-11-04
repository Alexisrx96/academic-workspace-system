from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3

from .source_config import load_source_configs


_DB_PATH = ".blackboard-sync/search.sqlite3"


@dataclass(frozen=True, slots=True)
class SearchResult:
    title: str
    excerpt: str
    path: str
    lane: str
    course: str
    source_url: str | None = None
    score: float | None = None
    chunk_id: str | None = None
    content_hash: str | None = None
    text: str | None = None


def _metadata(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    values = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip('"')
    return values


def _title(path: Path, text: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else path.stem


def _body(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end >= 0:
            text = text[end + 5 :]
    return re.sub(r"\s+", " ", text).strip()


def _documents(target: Path):
    seen: set[str] = set()
    for source in load_source_configs(target):
        root = target / source.root
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md")):
            relative = path.relative_to(target).as_posix()
            if relative in seen or path.name.lower() == "index.md" or path.name.lower().startswith("ultradocumentbody"):
                continue
            seen.add(relative)
            text = path.read_text(encoding="utf-8", errors="replace")
            metadata = _metadata(text)
            course = path.relative_to(root).parts[0] if path.relative_to(root).parts else ""
            yield relative, _title(path, text), _body(text), "official", course, metadata.get("source_url")
    external = target / "Recursos Externos"
    if external.exists():
        for path in sorted(external.rglob("*.md")):
            relative = path.relative_to(target).as_posix()
            if relative in seen:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            metadata = _metadata(text)
            courses = metadata.get("related_courses", "")
            try:
                parsed_courses = json.loads(courses)
                if isinstance(parsed_courses, list):
                    courses = ", ".join(str(course) for course in parsed_courses)
            except json.JSONDecodeError:
                pass
            yield relative, _title(path, text), _body(text), "external", courses, metadata.get("source_url")


def rebuild_search_index(target: Path, database: Path | None = None) -> Path:
    target = Path(target)
    database = Path(database) if database else target / _DB_PATH
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE IF EXISTS documents")
        connection.execute("CREATE VIRTUAL TABLE documents USING fts5(doc_id UNINDEXED, title, body, path UNINDEXED, lane UNINDEXED, course UNINDEXED, source_url UNINDEXED)")
        connection.executemany(
            "INSERT INTO documents(doc_id,title,body,path,lane,course,source_url) VALUES (?,?,?,?,?,?,?)",
            ((path, title, body, path, lane, course, source_url) for path, title, body, lane, course, source_url in _documents(target)),
        )
        connection.commit()
    return database


def search(target: Path, query: str, *, course: str | None = None, lane: str | None = None, limit: int = 10) -> tuple[SearchResult, ...]:
    terms = re.findall(r"[\wáéíóúüñ]{2,}", query.lower())
    if not terms:
        return ()
    match = " AND ".join(f'"{term.replace(chr(34), "")}"' for term in terms)
    database = Path(target) / _DB_PATH
    if not database.is_file():
        rebuild_search_index(target, database)
    clauses = ["documents MATCH ?"]
    params: list[object] = [match]
    if course:
        clauses.append("course = ?")
        params.append(course)
    if lane:
        clauses.append("lane = ?")
        params.append(lane)
    params.append(limit)
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT title, snippet(documents, 2, '', '', ' … ', 36), path, lane, course, source_url "
            f"FROM documents WHERE {' AND '.join(clauses)} "
            "ORDER BY CASE lane WHEN 'official' THEN 0 ELSE 1 END, bm25(documents) LIMIT ?",
            params,
        ).fetchall()
    return tuple(SearchResult(*row) for row in rows)
