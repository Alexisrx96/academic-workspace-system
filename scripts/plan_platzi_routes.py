from __future__ import annotations

import argparse
import json
from pathlib import Path

from academic_workspace.platzi_route_plan import build_route_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Construye un plan determinista de rutas Platzi")
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_route_plan(json.loads(args.catalog.read_text(encoding="utf-8")), json.loads(args.config.read_text(encoding="utf-8")))
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
