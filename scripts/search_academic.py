from __future__ import annotations

import argparse
import json
from pathlib import Path

from academic_workspace.search_index import rebuild_search_index, search
from academic_workspace.resource_registry import add_semantic_relations, rebuild_resource_registry
from academic_workspace.semantic_search import SentenceTransformerProvider, rebuild_semantic_index, semantic_search


def main() -> int:
    parser = argparse.ArgumentParser(description="Busca localmente en fuentes académicas y material externo")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("query")
    parser.add_argument("--course")
    parser.add_argument("--lane", choices=("official", "external"))
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--rebuild-registry", action="store_true", help="reconstruye el catálogo local de recursos y relaciones")
    parser.add_argument("--semantic-relations", action="store_true", help="genera sugerencias de relación desde el índice semántico")
    parser.add_argument("--relation-threshold", type=float, default=0.78)
    parser.add_argument("--relation-top-k", type=int, default=3)
    parser.add_argument("--mode", choices=("lexical", "semantic", "hybrid"), default="lexical")
    parser.add_argument("--semantic-model", help="Ruta local de un modelo sentence-transformers")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    registry = None
    if args.rebuild_registry or args.semantic_relations:
        registry = rebuild_resource_registry(args.target)
    if args.rebuild:
        rebuild_search_index(args.target)
    lexical = search(args.target, args.query, course=args.course, lane=args.lane) if args.mode in {"lexical", "hybrid"} else ()
    semantic = ()
    if args.mode in {"semantic", "hybrid"}:
        if not args.semantic_model:
            parser.error("--semantic-model es obligatorio para --mode semantic o hybrid")
        provider = SentenceTransformerProvider(args.semantic_model)
        if args.rebuild:
            rebuild_semantic_index(args.target, provider)
        semantic = semantic_search(args.target, args.query, provider, course=args.course, lane=args.lane)
    if args.semantic_relations:
        if not args.semantic_model:
            parser.error("--semantic-model es obligatorio para --semantic-relations")
        provider = SentenceTransformerProvider(args.semantic_model)
        semantic_database = args.target / ".blackboard-sync" / "semantic-search.sqlite3"
        if args.rebuild:
            rebuild_semantic_index(args.target, provider, semantic_database)
        add_semantic_relations(registry, semantic_database, provider, threshold=args.relation_threshold, top_k=args.relation_top_k)
    if args.mode == "lexical":
        results = lexical
    elif args.mode == "semantic":
        results = semantic
    else:
        merged = {result.path: result for result in semantic}
        merged.update({result.path: result for result in lexical})
        results = tuple(sorted(merged.values(), key=lambda result: (0 if result.lane == "official" else 1, result.path)))
    payload = [
        {
            "title": result.title,
            "excerpt": result.excerpt,
            "path": result.path,
            "lane": result.lane,
            "course": result.course,
            "source_url": result.source_url,
            "score": result.score,
            "chunk_id": result.chunk_id,
        }
        for result in results
    ]
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for result in payload:
            print(f"[{result['lane']}] {result['title']} — {result['path']}\n  {result['excerpt']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
