from __future__ import annotations

import math
from pathlib import Path
import re
from typing import Any

from .knowledge_graph import expand_results
from .search_index import SearchResult, search
from .semantic_search import SentenceTransformerProvider, semantic_search

_STOPWORDS = {
    "a", "al", "cómo", "con", "de", "del", "el", "en", "es", "la", "las", "los",
    "para", "por", "que", "se", "su", "un", "una", "y",
}


def _merge_results(lexical: tuple[SearchResult, ...], semantic: tuple[SearchResult, ...]) -> tuple[SearchResult, ...]:
    merged: dict[tuple[str, str | None], SearchResult] = {}
    for result in semantic + lexical:
        key = (result.path, result.chunk_id)
        if key not in merged:
            merged[key] = result
    return tuple(sorted(merged.values(), key=lambda item: (0 if item.lane == "official" else 1, -(item.score or 0), item.path, item.chunk_id or "")))


def _lexical_retrieve(target: Path, query: str, *, course: str | None, lane: str | None, limit: int) -> tuple[SearchResult, ...]:
    direct = search(target, query, course=course, lane=lane, limit=limit)
    if direct:
        return direct
    terms = [term for term in re.findall(r"[\wáéíóúüñ]{3,}", query.lower()) if term not in _STOPWORDS]
    candidates: dict[str, tuple[int, SearchResult]] = {}
    for term in terms:
        for result in search(target, term, course=course, lane=lane, limit=limit):
            count, previous = candidates.get(result.path, (0, result))
            candidates[result.path] = (count + 1, previous)
    ranked = sorted(candidates.values(), key=lambda item: (-item[0], 0 if item[1].lane == "official" else 1, item[1].path))
    return tuple(result for _count, result in ranked[:limit])


def build_rag_context(
    target: Path,
    query: str,
    *,
    mode: str = "lexical",
    semantic_model: str | None = None,
    course: str | None = None,
    lane: str | None = None,
    max_chunks: int = 8,
    max_chars: int = 6000,
    graph_hops: int = 1,
    graph_nodes: int = 12,
) -> dict[str, Any]:
    """Build bounded, citable context, optionally expanded through the local graph."""
    if mode not in {"lexical", "semantic", "hybrid", "graph-hybrid"}:
        raise ValueError("mode debe ser lexical, semantic, hybrid o graph-hybrid")
    if max_chunks < 1 or max_chars < 1:
        raise ValueError("max_chunks y max_chars deben ser positivos")
    lexical = _lexical_retrieve(target, query, course=course, lane=lane, limit=max_chunks) if mode in {"lexical", "hybrid", "graph-hybrid"} else ()
    semantic: tuple[SearchResult, ...] = ()
    if mode in {"semantic", "hybrid", "graph-hybrid"}:
        if mode in {"semantic", "hybrid"} and not semantic_model:
            raise ValueError("semantic_model es obligatorio para semantic/hybrid")
        if semantic_model:
            semantic = semantic_search(
                target, query, SentenceTransformerProvider(semantic_model), course=course, lane=lane, limit=max_chunks
            )
    seeds = _merge_results(lexical, semantic)[:max_chunks]
    graph_results: tuple[SearchResult, ...] = ()
    if mode == "graph-hybrid":
        graph_results = expand_results(
            target, seeds, course=course, lane=lane, max_hops=graph_hops, max_nodes=graph_nodes
        )
    if mode == "graph-hybrid":
        # Preserve direct evidence first, then spend remaining budget on graph context.
        combined: list[SearchResult] = []
        seen_paths: set[str] = set()
        for result in seeds + graph_results:
            if result.path in seen_paths:
                continue
            seen_paths.add(result.path)
            combined.append(result)
            if len(combined) >= max_chunks:
                break
        results = tuple(combined)
    else:
        results = _merge_results(seeds, graph_results)[:max_chunks]
    sources = []
    blocks = []
    used = 0
    for index, result in enumerate(results, start=1):
        citation = f"[S{index}]"
        source = {
            "citation": citation,
            "title": result.title,
            "path": result.path,
            "lane": result.lane,
            "course": result.course,
            "source_url": result.source_url,
            "score": result.score,
            "chunk_id": result.chunk_id,
            "retrieval": "graph" if (result.chunk_id or "").startswith("graph:") else "seed",
        }
        block = f"{citation} {result.title}\nRuta: {result.path}\nContenido: {(result.text or result.excerpt).strip()}\n"
        remaining = max_chars - used
        if remaining <= 0:
            break
        if len(block) > remaining:
            block = block[:remaining].rstrip()
        blocks.append(block)
        sources.append(source)
        used += len(block) + (2 if used else 0)
        if used >= max_chars:
            break
    context = "\n\n".join(blocks)[:max_chars]
    prompt = (
        "Responde únicamente con base en el contexto recuperado. "
        "Si no hay evidencia suficiente, indícalo. Cita las fuentes usando [S1], [S2], etc.\n\n"
        f"Pregunta: {query}\n\nContexto:\n{context}"
    )
    return {
        "schema": "rag-context.v2",
        "query": query,
        "mode": mode,
        "graph": {"enabled": mode == "graph-hybrid", "hops": graph_hops, "max_nodes": graph_nodes, "seed_count": len(seeds), "expanded_count": len(graph_results)},
        "context": context,
        "prompt": prompt,
        "sources": sources,
        "result_count": len(sources),
        "char_count": len(context),
        "token_estimate": math.ceil(len(prompt) / 4),
    }
