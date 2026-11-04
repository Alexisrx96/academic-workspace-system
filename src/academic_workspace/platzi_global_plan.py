from __future__ import annotations

from typing import Any


def build_global_route_order(routes: list[dict[str, Any]], course_catalog: dict[str, Any], *, weekly_minutes: int, minutes_per_course: int = 30) -> dict[str, Any]:
    courses_by_route = {str(item.get("route_url")): {str(course.get("url")) for course in item.get("courses", ()) if course.get("url")} for item in course_catalog.get("routes", ())}
    excluded = []
    remaining = {}
    for route in routes:
        name = str(route.get("name", ""))
        if int(route.get("course_count") or 0) == 0 or "deprecated" in name.casefold():
            excluded.append({"name": name, "url": route.get("url"), "reason": "sin cursos activos o deprecated"})
        else:
            remaining[str(route.get("url"))] = dict(route)
    covered: set[str] = set()
    selected = []
    capacity = max(0, int(weekly_minutes))
    while remaining:
        candidates = []
        for url, route in remaining.items():
            course_set = courses_by_route.get(url, set())
            incremental = len(course_set - covered)
            estimated_remaining = round(max(0, int(route.get("course_count") or 0) * (1 - float(route.get("progress_percent") or 0) / 100)))
            candidates.append((incremental, estimated_remaining, -float(route.get("progress_percent") or 0), str(route.get("name", "")).casefold(), url, course_set, route))
        incremental, estimated_remaining, _progress, _name, url, course_set, route = min(candidates)
        covered.update(course_set)
        planned = min(capacity, incremental * minutes_per_course)
        capacity -= planned
        selected.append({"name": route.get("name"), "url": url, "course_count": route.get("course_count"), "progress_percent": route.get("progress_percent"), "incremental_courses": incremental, "estimated_remaining_courses": estimated_remaining, "planned_minutes": planned, "reason": "maximiza cursos compartidos ya cubiertos y minimiza cursos nuevos"})
        remaining.pop(url)
    return {"schema": "platzi-global-route-plan.v1", "weekly_minutes": int(weekly_minutes), "minutes_per_course": minutes_per_course, "route_count": len(selected),
 "input_route_count": len(routes),
 "excluded_routes": excluded, "unique_courses_total": len(covered), "routes": selected, "remaining_weekly_minutes": capacity, "course_catalog_status": "complete" if courses_by_route and all(str(route.get("url")) in courses_by_route for route in routes) else "partial", "determinism": {"model_used": False, "algorithm": "greedy_set_cover_with_progress_tiebreak"}}
