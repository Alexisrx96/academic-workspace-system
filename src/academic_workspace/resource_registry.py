from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sqlite3

from .search_index import _documents, _metadata, _body, _title
from .semantic_search import EmbeddingProvider, _cosine, _unpack


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _work_documents(target: Path):
    excluded = {"Blackboard", "Blackboard-UTEC", "Recursos Externos", ".blackboard-sync", "Control Académico", "_backups", "_exports"}
    for path in sorted(target.rglob("*.md")):
        relative = path.relative_to(target).as_posix()
        if relative.split("/", 1)[0] in excluded:
            continue
        if relative.startswith(".obsidian/"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        yield relative, _title(path, text), _body(text), "work", "", _metadata(text)


def _explicit_targets(text: str) -> list[str]:
    values = re.findall(r"source_ref\s*:\s*[\"']?\[\[([^\]|]+)", text)
    return [value.strip().replace("\\", "/") + (".md" if not value.strip().endswith(".md") else "") for value in values]


def rebuild_resource_registry(target: Path, database: Path | None = None) -> Path:
    target = Path(target)
    database = Path(database) if database else target / ".blackboard-sync" / "resource-registry.sqlite3"
    database.parent.mkdir(parents=True, exist_ok=True)
    records = []
    seen: set[str] = set()
    for path, title, body, lane, course, source_url in _documents(target):
        if path in seen:
            continue
        seen.add(path)
        full = target / path
        text = full.read_text(encoding="utf-8", errors="replace")
        records.append((path, title, lane, course, source_url or "", _hash(text), _hash(body)))
    for path, title, body, lane, course, metadata in _work_documents(target):
        if path in seen:
            continue
        seen.add(path)
        full = target / path
        text = full.read_text(encoding="utf-8", errors="replace")
        records.append((path, title, lane, course, metadata.get("source_url", ""), _hash(text), _hash(body)))

    with sqlite3.connect(database) as connection:
        connection.executescript("""
            DROP TABLE IF EXISTS relations;
            DROP TABLE IF EXISTS resources;
            CREATE TABLE resources (
                resource_id TEXT PRIMARY KEY, path TEXT UNIQUE NOT NULL, title TEXT NOT NULL,
                lane TEXT NOT NULL, course TEXT NOT NULL, source_url TEXT, content_hash TEXT NOT NULL,
                body_hash TEXT NOT NULL
            );
            CREATE TABLE relations (
                relation_type TEXT NOT NULL, from_path TEXT NOT NULL, to_path TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 1.0, model_id TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (relation_type, from_path, to_path)
            );
        """)
        connection.executemany(
            "INSERT INTO resources VALUES (?,?,?,?,?,?,?,?)",
            ((_hash(path), path, title, lane, course, source_url, content_hash, body_hash) for path, title, lane, course, source_url, content_hash, body_hash in records),
        )
        known = {path for path, *_ in records}
        relations = []
        for path, *_ in records:
            text = (target / path).read_text(encoding="utf-8", errors="replace")
            for candidate in _explicit_targets(text):
                if candidate in known:
                    relations.append(("explicit_link", path, candidate, 1.0, ""))

        # Deterministic structural edges: nearby resources in one Blackboard unit.
        # Keep only the nearest three per resource to bound graph expansion.
        by_scope: dict[str, list[str]] = {}
        for path, *_ in records:
            parts = path.split("/")
            if len(parts) >= 4 and parts[0] == "Blackboard-UTEC":
                scope = "/".join(parts[:4])
                by_scope.setdefault(scope, []).append(path)
        for paths in by_scope.values():
            ordered = sorted(paths)
            for path in ordered:
                neighbors = [candidate for candidate in ordered if candidate != path][:3]
                relations.extend(("same_unit", path, candidate, 0.7, "structure-v1") for candidate in neighbors)
        connection.executemany("INSERT OR IGNORE INTO relations VALUES (?,?,?,?,?)", relations)
        connection.execute("CREATE INDEX resources_lane ON resources(lane)")
        connection.execute("CREATE INDEX resources_course ON resources(course)")
        connection.commit()
    return database


def add_semantic_relations(
    registry: Path,
    semantic_database: Path,
    provider: EmbeddingProvider,
    *,
    threshold: float = 0.78,
    top_k: int = 3,
) -> int:
    """Persist bidirectional semantic suggestions; never overwrite explicit links."""
    if not 0 <= threshold <= 1:
        raise ValueError("threshold debe estar entre 0 y 1")
    if top_k < 1:
        raise ValueError("top_k debe ser positivo")
    registry = Path(registry)
    semantic_database = Path(semantic_database)
    with sqlite3.connect(semantic_database) as semantic:
        rows = semantic.execute(
            "SELECT path, vector, model_id FROM semantic_documents WHERE model_id = ?",
            (provider.model_id,),
        ).fetchall()
    if not rows:
        raise ValueError("no hay embeddings compatibles con el modelo solicitado")

    by_path: dict[str, list[list[float]]] = {}
    for path, vector, _model_id in rows:
        by_path.setdefault(path, []).append(_unpack(vector))
    paths = sorted(by_path)
    suggestions: set[tuple[str, str, float]] = set()
    for path in paths:
        candidates = []
        for other in paths:
            if other == path:
                continue
            score = max(_cosine(left, right) for left in by_path[path] for right in by_path[other])
            if score >= threshold:
                candidates.append((score, other))
        for score, other in sorted(candidates, key=lambda item: (-item[0], item[1]))[:top_k]:
            suggestions.add((path, other, score))
            suggestions.add((other, path, score))

    with sqlite3.connect(registry) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(relations)")}
        if "model_id" not in columns:
            connection.execute("ALTER TABLE relations ADD COLUMN model_id TEXT NOT NULL DEFAULT ''")
        connection.execute("DELETE FROM relations WHERE relation_type = 'semantic_related' AND model_id = ?", (provider.model_id,))
        connection.executemany(
            "INSERT OR REPLACE INTO relations VALUES (?,?,?,?,?)",
            (("semantic_related", left, right, score, provider.model_id) for left, right, score in suggestions),
        )
        connection.commit()
    return len(suggestions)
