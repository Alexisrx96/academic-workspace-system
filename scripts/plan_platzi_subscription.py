from __future__ import annotations

import argparse
import json
from pathlib import Path

from academic_workspace.platzi_subscription_plan import build_subscription_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan determinista de suscripción Platzi")
    parser.add_argument("--routes", type=Path, required=True)
    parser.add_argument("--courses", type=Path, required=True)
    parser.add_argument("--weeks", type=int, default=16)
    parser.add_argument("--max-courses-per-week", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    routes = json.loads(args.routes.read_text(encoding="utf-8"))["routes"]
    catalog = json.loads(args.courses.read_text(encoding="utf-8"))
    result = build_subscription_plan(routes, catalog, weeks=args.weeks, max_courses_per_week=args.max_courses_per_week)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"anchor": result["anchor_route"], "weeks": len(result["weekly_plan"]), "active_routes": result["active_route_count"], "unique_courses": result["unique_course_count_observed"], "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
