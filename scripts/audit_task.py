from __future__ import annotations

import argparse
import json
from pathlib import Path

from academic_workspace.task_control import audit_task


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita una tarea académica contra su rúbrica")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = audit_task(args.task, args.target)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['title']}: {result['status']} ({result['score']:.0%})")
        for criterion in result["criteria"]:
            print(f"- [{criterion['status']}] {criterion['criterion']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
