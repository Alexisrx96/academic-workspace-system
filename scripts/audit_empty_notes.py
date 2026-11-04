from __future__ import annotations

import argparse
import json
from pathlib import Path

from academic_workspace.empty_notes import audit_empty_notes, write_empty_notes_audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita notas Markdown vacías o solo con título sin eliminarlas")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--near-empty-chars", type=int, default=0)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit_empty_notes(args.target, near_empty_chars=args.near_empty_chars)
    if args.write_report:
        report["report_path"] = write_empty_notes_audit(args.target, near_empty_chars=args.near_empty_chars).relative_to(args.target).as_posix()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
        for item in report["items"]:
            print(f"[{item['action']}] [{item['lane']}] {item['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
