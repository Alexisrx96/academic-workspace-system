from __future__ import annotations

import argparse
import json
from pathlib import Path

from academic_workspace.empty_notes import audit_empty_notes, quarantine_empty_notes


def main() -> int:
    parser = argparse.ArgumentParser(description="Mueve hojas Markdown vacías a cuarentena reversible")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--apply", action="store_true", help="ejecuta el movimiento; sin esto solo audita")
    args = parser.parse_args()
    if not args.apply:
        report = audit_empty_notes(args.target)
        prefix = args.prefix.strip("/").replace("\\", "/") + "/"
        items = [item for item in report["items"] if item["path"].startswith(prefix) and item["action"] == "review_leaf"]
        print(json.dumps({"mode": "dry-run", "prefix": args.prefix, "candidate_count": len(items), "items": items}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(quarantine_empty_notes(args.target, args.prefix, run_id=args.run_id), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
