from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import sqlite3
import struct
from typing import Protocol, Sequence

from .search_index import SearchResult, _documents


class EmbeddingProvider(Protocol):
    model_id: str

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        ...


@dataclass(frozen=True, slots=True)
class SentenceTransformerProvider:
    model_path: str

    @property
    def model_id(self) -> str:
        return f"sentence-transformers:{self.model_path}"

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError("Instala el extra embeddings o proporciona otro EmbeddingProvider local") from error
        model = SentenceTransformer(self.model_path, local_files_only=True)
        vectors = model.encode(list(texts), normalize_embeddings=True)
        return [list(map(float, vector)) for vector in vectors]


def _pack(vector: list[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def _unpack(data: bytes) -> list[float]:
    size = len(data) // 4
    return list(struct.unpack(f"<{size}f", data))


def _cosine(left: list[float], right: list[float]) -> float:
    denominator = math.sqrt(sum(value * value for value in left) * sum(value * value for value in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0.0


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _chunks(text: str, *, chunk_chars: int = 900, overlap: int = 120) -> list[tuple[int, str]]:
    """Split normalized text deterministically, preferring paragraph boundaries."""
    if chunk_chars <= overlap:
        raise ValueError("chunk_chars debe ser mayor que overlap")
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    chunks: list[tuple[int, str]] = []
    current = ""
    for paragraph in paragraphs or [text]:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if current and len(candidate) > chunk_chars:
            chunks.append((len(chunks), current))
            tail = current[-overlap:].lstrip()
            current = f"{tail}\n\n{paragraph}".strip()
        else:
            current = candidate
    if current:
        chunks.append((len(chunks), current))
    return chunks


def _schema_is_current(connection: sqlite3.Connection) -> bool:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(semantic_documents)")}
    return {"chunk_id", "content_hash", "model_id", "vector", "chunk_text"}.issubset(columns)


def rebuild_semantic_index(
    target: Path,
    provider: EmbeddingProvider,
    database: Path | None = None,
    *,
    chunk_chars: int = 900,
    overlap: int = 120,
) -> Path:
    target = Path(target)
    database = Path(database) if database else target / ".blackboard-sync" / "semantic-search.sqlite3"
    database.parent.mkdir(parents=True, exist_ok=True)
    documents = list(_documents(target))

    with sqlite3.connect(database) as connection:
        if not _schema_is_current(connection):
            connection.execute("DROP TABLE IF EXISTS semantic_documents")
            connection.execute(
                "CREATE TABLE semantic_documents ("
                "chunk_id TEXT PRIMARY KEY, path TEXT NOT NULL, title TEXT NOT NULL, excerpt TEXT NOT NULL, "
                "lane TEXT NOT NULL, course TEXT NOT NULL, source_url TEXT, section TEXT, ordinal INTEGER NOT NULL, "
                "content_hash TEXT NOT NULL, chunk_text TEXT NOT NULL, vector BLOB NOT NULL, model_id TEXT NOT NULL)"
            )
        existing = {
            row[0]: row[1:]
            for row in connection.execute("SELECT chunk_id, content_hash, vector, model_id FROM semantic_documents")
            if row[3] == provider.model_id
        }
        planned: list[tuple[str, str, str, str, str, str, str | None, int, str, str]] = []
        for path, title, body, lane, course, source_url in documents:
            for ordinal, chunk in _chunks(body, chunk_chars=chunk_chars, overlap=overlap):
                chunk_id = hashlib.sha256(f"{path}\n{ordinal}\n{chunk}".encode("utf-8")).hexdigest()
                planned.append((chunk_id, path, title, chunk[:320], lane, course, source_url, ordinal, _content_hash(chunk), chunk))

        missing = [item for item in planned if item[0] not in existing or existing[item[0]][0] != item[8]]
        vectors = iter(provider.encode([f"{item[2]}\n{item[3]}" for item in missing])) if missing else iter(())
        connection.execute("DELETE FROM semantic_documents")
        rows = []
        missing_by_id = {item[0]: _pack(vector) for item, vector in zip(missing, vectors)}
        for item in planned:
            chunk_id, path, title, excerpt, lane, course, source_url, ordinal, content_hash, chunk_text = item
            vector = missing_by_id[chunk_id] if chunk_id in missing_by_id else existing[chunk_id][1]
            rows.append((chunk_id, path, title, excerpt, lane, course, source_url, "", ordinal, content_hash, chunk_text, vector, provider.model_id))
        connection.executemany("INSERT INTO semantic_documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        connection.execute("CREATE INDEX IF NOT EXISTS semantic_documents_course ON semantic_documents(course)")
        connection.execute("CREATE INDEX IF NOT EXISTS semantic_documents_path ON semantic_documents(path)")
        connection.commit()
    return database


def semantic_search(
    target: Path,
    query: str,
    provider: EmbeddingProvider,
    *,
    database: Path | None = None,
    course: str | None = None,
    lane: str | None = None,
    limit: int = 10,
) -> tuple[SearchResult, ...]:
    database = Path(database) if database else Path(target) / ".blackboard-sync" / "semantic-search.sqlite3"
    if not database.is_file():
        rebuild_semantic_index(target, provider, database)
    else:
        with sqlite3.connect(database) as connection:
            current_schema = _schema_is_current(connection)
        if not current_schema:
            rebuild_semantic_index(target, provider, database)
    query_vector = provider.encode([query])[0]
    clauses: list[str] = ["model_id = ?"]
    params: list[str] = [provider.model_id]
    if course:
        clauses.append("course = ?")
        params.append(course)
    if lane:
        clauses.append("lane = ?")
        params.append(lane)
    where = f" WHERE {' AND '.join(clauses)}"
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT chunk_id, title, excerpt, chunk_text, path, lane, course, source_url, vector, content_hash "
            f"FROM semantic_documents{where}", params
        ).fetchall()
    ranked = []
    for chunk_id, title, excerpt, chunk_text, path, row_lane, row_course, source_url, vector, content_hash in rows:
        score = _cosine(query_vector, _unpack(vector))
        result = SearchResult(title, excerpt, path, row_lane, row_course, source_url, score, chunk_id, content_hash, chunk_text)
        ranked.append((result, score))
    ranked.sort(key=lambda item: (0 if item[0].lane == "official" else 1, -item[1], item[0].path, item[0].chunk_id or ""))
    return tuple(result for result, _score in ranked[:limit])
