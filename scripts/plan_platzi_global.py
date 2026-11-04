from __future__ import annotations

import argparse
import json
from pathlib import Path

from academic_workspace.platzi_global_plan import build_global_route_order


def main() -> int:
    parser = argparse.ArgumentParser(description="Ordena todas las rutas Platzi por cobertura global de cursos")
    parser.add_argument("--routes", type=Path, required=True)
    parser.add_argument("--courses", type=Path, required=True)
    parser.add_argument("--weekly-minutes", type=int, default=300)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    routes = json.loads(args.routes.read_text(encoding="utf-8"))["routes"]
    courses = json.loads(args.courses.read_text(encoding="utf-8"))
    result = build_global_route_order(routes, courses, weekly_minutes=args.weekly_minutes)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"routes": result["route_count"], "unique_courses": result["unique_courses_total"], "catalog_status": result["course_catalog_status"], "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
