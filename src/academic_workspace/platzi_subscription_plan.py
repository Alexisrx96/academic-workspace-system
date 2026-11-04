from __future__ import annotations

from collections import Counter
from typing import Any
from urllib.parse import urlparse


def _is_course_url(url: str) -> bool:
    path = urlparse(url).path.strip("/").split("/")
    return len(path) == 2 and path[0] == "cursos" and bool(path[1])


def _category(name: str) -> tuple[int, str]:
    text = name.casefold()
    if any(k in text for k in ("matem", "estadística", "estadistica", "probabilidad", "álgebra", "calculo", "cálculo")):
        return 1, "matematica-estadistica"
    if any(k in text for k in ("inteligencia artificial", "machine learning", "deep learning", "llm", "ia ", "ai ", "agentes")):
        return 0, "ia"
    if any(k in text for k in ("inglés", "english")):
        return 2, "ingles"
    return 3, "no-tecnica"


def build_subscription_plan(routes: list[dict[str, Any]], catalog: dict[str, Any], *, weeks: int = 16, minutes_per_course: int = 300, max_courses_per_week: int = 1) -> dict[str, Any]:
    raw_by_route = {str(item.get("route_url")): item for item in catalog.get("routes", ())}
    route_courses: dict[str, set[str]] = {}
    title_by_course: dict[str, str] = {}
    for route in routes:
        url = str(route.get("url")); item = raw_by_route.get(url, {})
        route_courses[url] = set()
        for course in item.get("courses", ()):
            course_url = str(course.get("url", ""))
            if _is_course_url(course_url):
                route_courses[url].add(course_url)
                title_by_course.setdefault(course_url, str(course.get("title", "")))
    course_routes = Counter(course for courses in route_courses.values() for course in courses)
    active, excluded = [], []
    for route in routes:
        url = str(route.get("url")); name = str(route.get("name", "")); count = int(route.get("course_count") or 0)
        if count == 0 or "deprecated" in name.casefold():
            excluded.append({"name": name, "url": url, "reason": "sin cursos activos o deprecated"}); continue
        rank, category = _category(name)
        shared = {course for course in route_courses.get(url, set()) if course_routes[course] >= 3}
        remaining = round(max(0, count * (1 - float(route.get("progress_percent") or 0) / 100)))
        active.append({**route, "category_rank": rank, "category": category, "courses": route_courses.get(url, set()), "shared_courses": shared, "remaining_estimated": remaining, "shared_route_count": len(shared)})
    if not active:
        cadence = {"ia": min(10, max_courses_per_week), "matematica-estadistica": min(10, max_courses_per_week), "ingles": min(10, max_courses_per_week), "no-tecnica": min(6, max_courses_per_week)}
        return {"schema": "platzi-subscription-plan.v1", "subscription_horizon_weeks": weeks, "course_per_week": max_courses_per_week, "cadence_policy": cadence, "weekly_plan": [], "route_status": [], "active_route_count": 0, "excluded_routes": excluded, "unique_course_count_observed": 0, "theoretical_completion_weeks_at_one_course_per_week": 0, "courses_possible_in_horizon": 0, "determinism": {"model_used": False}}
    anchor_candidates = [r for r in active if r["shared_route_count"] > 0]
    anchor = min(anchor_candidates, key=lambda r: (r["category_rank"], r["remaining_estimated"], -r["shared_route_count"], r["name"].casefold())) if anchor_candidates else min(active, key=lambda r: (r["category_rank"], r["remaining_estimated"], r["name"].casefold()))
    completed_courses: set[str] = set(); weekly = []
    cadence_policy = {"ia": min(10, max_courses_per_week), "matematica-estadistica": min(10, max_courses_per_week), "ingles": min(10, max_courses_per_week), "no-tecnica": min(6, max_courses_per_week)}
    for week in range(1, max(0, weeks) + 1):
        used_categories: dict[str, int] = {}
        for _slot in range(max(0, max_courses_per_week)):
            candidates = []
            for route in active:
                new = route["courses"] - completed_courses
                shared_new = new & {c for c, n in course_routes.items() if n >= 3}
                for course in new:
                    coverage = course_routes[course]
                    anchor_bonus = 1 if route["url"] == anchor["url"] and week == 1 else 0
                    score = (anchor_bonus, -route["category_rank"], coverage, len(shared_new), -route["remaining_estimated"], -len(new), course)
                    candidates.append((score, course, route, coverage))
            candidates = [x for x in candidates if used_categories.get(x[2]["category"], 0) < cadence_policy[x[2]["category"]]]
            if not candidates: break
            _score, course, route, coverage = max(candidates, key=lambda x: x[0])
            completed_courses.add(course); used_categories[route["category"]] = used_categories.get(route["category"], 0) + 1
            title = title_by_course.get(course, "")
            effort = "deep" if any(k in title.casefold() for k in ("proyecto", "avanzado", "machine learning", "deep learning", "álgebra lineal", "estadística inferencial")) else "screening"
            weekly.append({"week": week, "course_url": course, "course_title": title, "route": route["name"], "route_url": route["url"], "category": route["category"], "route_category_rank": route["category_rank"], "covered_by_route_count": coverage, "effort_mode": effort, "reason": "tronco compartido + prioridad + cadencia adaptativa"})
        if not any(r["courses"] - completed_courses for r in active): break
    route_status = []
    for route in active:
        remaining_courses = route["courses"] - completed_courses
        route_status.append({"name": route["name"], "url": route["url"], "category": route["category"], "progress_percent": route.get("progress_percent"), "course_count": route.get("course_count"), "courses_observed": len(route["courses"]), "courses_in_plan": len(route["courses"] & completed_courses), "estimated_remaining_after_plan": max(0, route["remaining_estimated"] - len(route["courses"] & completed_courses)), "status": "complete" if route["courses"] and len(route["courses"]) >= int(route.get("course_count") or 0) and not remaining_courses else "in_progress"})
    route_status.sort(key=lambda r: (0 if r["status"] == "complete" else 1, r["category"], r["estimated_remaining_after_plan"], r["name"].casefold()))
    unique = len(set().union(*(r["courses"] for r in active)))
    return {"schema": "platzi-subscription-plan.v1", "subscription_horizon_weeks": weeks, "course_per_week": max_courses_per_week, "minutes_per_course": minutes_per_course, "cadence_policy": cadence_policy, "goal": "maximizar rutas completadas mediante cursos compartidos, manteniendo rotación prioritaria", "priority_order": ["ia", "matematica-estadistica", "ingles", "no-tecnica"], "anchor_route": {"name": anchor["name"], "url": anchor["url"], "remaining_estimated": anchor["remaining_estimated"], "shared_courses": anchor["shared_route_count"]}, "weekly_plan": weekly, "route_status": route_status, "active_route_count": len(active), "excluded_routes": excluded, "unique_course_count_observed": unique, "theoretical_completion_weeks_at_one_course_per_week": unique, "courses_possible_in_horizon": min(unique, max(0, weeks) * max_courses_per_week), "catalog_completeness_note": "La finalización de ruta requiere que su catálogo observable cubra el conteo declarado; no se marca complete con catálogo incompleto.", "determinism": {"model_used": False, "algorithm": "priority_then_shared_course_greedy_with_adaptive_cadence"}}
