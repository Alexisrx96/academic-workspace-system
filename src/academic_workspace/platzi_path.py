from __future__ import annotations

from typing import Any


def _course_tags(courses: dict[str, dict[str, Any]], raw_routes: list[dict[str, Any]]) -> dict[str, set[str]]:
    tags = {course_id: {str(tag) for tag in course.get("route_tags", course.get("routes", []))} for course_id, course in courses.items()}
    for route in raw_routes:
        route_id = str(route.get("id", route.get("name", "")))
        route_name = str(route.get("name", route_id))
        for course_id in route.get("course_ids", []):
            tags.setdefault(str(course_id), set()).update({route_id, route_name})
    return tags


def build_optimal_platzi_path(
    catalog: dict[str, Any],
    *,
    goals: list[str],
    weekly_minutes: int,
    target_routes: list[str] | None = None,
) -> dict[str, Any]:
    courses = {str(item["id"]): dict(item) for item in catalog.get("courses", [])}
    raw_routes = [dict(route) for route in catalog.get("routes", [])]
    tags = _course_tags(courses, raw_routes)
    goal_set = {goal.casefold() for goal in goals}
    goal_courses = {
        course_id for course_id, course in courses.items()
        if {str(skill).casefold() for skill in course.get("skills", [])} & goal_set
    }
    all_tags = set().union(*(tags.get(course_id, set()) for course_id in goal_courses)) if goal_courses else set()
    requested_tags = {str(tag) for tag in (target_routes or all_tags)}
    if not requested_tags:
        requested_tags = all_tags

    needed: set[str] = set(goal_courses)
    common_trunk = sorted(
        course_id for course_id, course_tags in tags.items()
        if len(course_tags & requested_tags) >= 2 and course_id not in goal_courses
    )
    needed.update(common_trunk)

    def include(course_id: str) -> None:
        if course_id in needed or course_id not in courses:
            return
        needed.add(course_id)
        for prerequisite in courses[course_id].get("prerequisites", []):
            include(str(prerequisite))

    for course_id in list(needed):
        for prerequisite in courses[course_id].get("prerequisites", []):
            include(str(prerequisite))

    ordered: list[str] = []
    visiting: set[str] = set()

    def visit(course_id: str) -> None:
        if course_id not in needed or course_id in ordered:
            return
        if course_id in visiting:
            raise ValueError(f"ciclo de prerequisitos en Platzi: {course_id}")
        visiting.add(course_id)
        for prerequisite in courses[course_id].get("prerequisites", []):
            visit(str(prerequisite))
        visiting.remove(course_id)
        ordered.append(course_id)

    for course_id in sorted(needed):
        visit(course_id)

    route_names = {}
    for route in raw_routes:
        route_id = str(route.get("id", route.get("name", "")))
        route_names[route_id] = str(route.get("name", route_id))
    remaining_capacity = max(0, int(weekly_minutes))
    elapsed = 0
    covered: set[str] = set()
    steps = []
    for course_id in ordered:
        course = courses[course_id]
        duration = max(0, int(course.get("duration_minutes", 0)))
        planned = min(duration, remaining_capacity)
        remaining_capacity -= planned
        elapsed += duration
        course_tags = tags.get(course_id, set())
        newly_covered = sorted((course_tags & requested_tags) - covered)
        covered.update(course_tags & requested_tags)
        reason = "tronco_comun" if course_id in common_trunk else "prerrequisito" if course_id not in goal_courses else "cubre_objetivo"
        steps.append({
            "course_id": course_id,
            "course": course.get("name", course_id),
            "route_tags": sorted(course_tags),
            "new_route_tags": newly_covered,
            "skills": [str(skill) for skill in course.get("skills", [])],
            "planned_minutes": planned,
            "remaining_minutes": duration - planned,
            "reason": reason,
        })
    covered_names = sorted(route_names.get(tag, tag) for tag in covered)
    uncovered_goals = sorted(goal for goal in goals if not any(goal.casefold() in {str(skill).casefold() for skill in courses[cid].get("skills", [])} for cid in goal_courses))
    return {
        "schema": "platzi-learning-path.v1",
        "goals": goals,
        "target_route_tags": sorted(requested_tags),
        "weekly_minutes": int(weekly_minutes),
        "estimated_total_minutes": elapsed,
        "common_trunk": common_trunk,
        "routes_covered": covered_names,
        "steps": steps,
        "uncovered_goals": uncovered_goals,
    }
