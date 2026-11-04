from __future__ import annotations

import argparse
import json
from pathlib import Path

from academic_workspace.task_control import calculate_weekly_quota


def main() -> int:
    parser = argparse.ArgumentParser(description="Calcula la cuota semanal de estudio")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = calculate_weekly_quota(json.loads(args.config.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"Cuota: {result['completed_minutes']}/{result['planned_minutes']} min; estado={result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
