from __future__ import annotations

import argparse
import json
from pathlib import Path

from academic_workspace.rag import build_rag_context


def main() -> int:
    parser = argparse.ArgumentParser(description="Construye contexto RAG local y citable sin invocar un modelo")
    parser.add_argument("query")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--mode", choices=("lexical", "semantic", "hybrid", "graph-hybrid"), default="lexical")
    parser.add_argument("--semantic-model")
    parser.add_argument("--graph-hops", type=int, default=1)
    parser.add_argument("--graph-nodes", type=int, default=12)
    parser.add_argument("--course")
    parser.add_argument("--lane", choices=("official", "external"))
    parser.add_argument("--max-chunks", type=int, default=8)
    parser.add_argument("--max-chars", type=int, default=6000)
    parser.add_argument("--format", choices=("json", "prompt", "context"), default="json")
    args = parser.parse_args()
    result = build_rag_context(
        args.target,
        args.query,
        mode=args.mode,
        semantic_model=args.semantic_model,
        course=args.course,
        lane=args.lane,
        max_chunks=args.max_chunks,
        max_chars=args.max_chars,
        graph_hops=args.graph_hops,
        graph_nodes=args.graph_nodes,
    )
    if args.format == "prompt":
        print(result["prompt"])
    elif args.format == "context":
        print(result["context"])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
