from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
import sqlite3

from .resource_registry import rebuild_resource_registry
from .search_index import SearchResult, _body


@dataclass(frozen=True, slots=True)
class GraphNeighbor:
    path: str
    relation_type: str
    distance: int
    confidence: float


def build_knowledge_graph(target: Path, database: Path | None = None) -> Path:
    """Build the deterministic academic graph as a projection of the resource registry.

    The registry remains the graph's source of truth. This function rebuilds it and
    returns the SQLite path so graph retrieval is reproducible and reversible.
    """
    return rebuild_resource_registry(target, database)


def _neighbors(
    connection: sqlite3.Connection,
    seeds: tuple[str, ...],
    *,
    max_hops: int,
    course: str | None,
    lane: str | None,
    max_nodes: int,
) -> tuple[GraphNeighbor, ...]:
    distances = {path: 0 for path in seeds}
    queue = deque(seeds)
    edges: dict[str, tuple[str, float, str]] = {}
    while queue and len(distances) < max_nodes:
        current = queue.popleft()
        distance = distances[current]
        if distance >= max_hops:
            continue
        rows = connection.execute(
            "SELECT relation_type, from_path, to_path, confidence FROM relations "
            "WHERE from_path = ? OR to_path = ? ORDER BY relation_type, from_path, to_path",
            (current, current),
        ).fetchall()
        for relation_type, left, right, confidence in rows:
            other = right if left == current else left
            if other in distances:
                continue
            row = connection.execute(
                "SELECT course, lane FROM resources WHERE path = ?", (other,)
            ).fetchone()
            if not row or (course and row[0] != course) or (lane and row[1] != lane):
                continue
            distances[other] = distance + 1
            edges[other] = (relation_type, float(confidence), current)
            queue.append(other)
            if len(distances) >= max_nodes:
                break
    return tuple(
        GraphNeighbor(path, edges[path][0], distances[path], edges[path][1])
        for path in sorted(edges, key=lambda path: (distances[path], path))
    )


def expand_results(
    target: Path,
    seeds: tuple[SearchResult, ...],
    *,
    course: str | None = None,
    lane: str | None = None,
    max_hops: int = 1,
    max_nodes: int = 12,
    database: Path | None = None,
) -> tuple[SearchResult, ...]:
    """Expand retrieved resources through explicit/semantic graph relations.

    Related resources are clearly marked with graph provenance in ``chunk_id``;
    their score is discounted by hop distance and relation confidence.
    """
    if max_hops < 1 or max_nodes < 1:
        raise ValueError("max_hops y max_nodes deben ser positivos")
    if not seeds:
        return ()
    database = build_knowledge_graph(target, database)
    seed_paths = tuple(sorted({result.path for result in seeds}))
    by_path: dict[str, SearchResult] = {}
    with sqlite3.connect(database) as connection:
        neighbors = _neighbors(
            connection, seed_paths, max_hops=max_hops, course=course, lane=lane, max_nodes=max_nodes
        )
        for neighbor in neighbors:
            row = connection.execute(
                "SELECT title, lane, course, source_url FROM resources WHERE path = ?",
                (neighbor.path,),
            ).fetchone()
            if not row:
                continue
            full = Path(target) / neighbor.path
            text = _body(full.read_text(encoding="utf-8", errors="replace")) if full.exists() else ""
            seed_score = max((result.score or 1.0) for result in seeds)
            score = seed_score * (0.8 ** neighbor.distance) * neighbor.confidence
            by_path.setdefault(
                neighbor.path,
                SearchResult(
                    row[0], text[:320], neighbor.path, row[1], row[2], row[3], score,
                    f"graph:{neighbor.relation_type}:{neighbor.distance}", None, text,
                ),
            )
    return tuple(by_path[path] for path in sorted(by_path, key=lambda path: (-(by_path[path].score or 0), path)))
