from __future__ import annotations

import argparse
import json
from pathlib import Path

from academic_workspace.platzi_path import build_optimal_platzi_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Optimiza una ruta Platzi por objetivos, tags y prerequisitos")
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--goal", action="append", required=True)
    parser.add_argument("--weekly-minutes", type=int, default=300)
    parser.add_argument("--route-tag", action="append")
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    result = build_optimal_platzi_path(catalog, goals=args.goal, weekly_minutes=args.weekly_minutes, target_routes=args.route_tag)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
