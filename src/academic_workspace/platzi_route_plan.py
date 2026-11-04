from __future__ import annotations

import re
from typing import Any

_DEFAULT_KEYWORDS = {
    "data_science": ("data", "datos", "data science", "analítica", "analisis", "analyst", "scientist"),
    "python": ("python",),
    "ai": ("inteligencia artificial", "ia", "ai", "llm", "agentes"),
    "machine_learning": ("machine learning", "deep learning", "ml"),
    "backend": ("backend", "desarrollo", "apis", "servidores", "devops"),
}


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold().replace("-", " ")).strip()


def build_route_plan(catalog: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    goals = [str(goal) for goal in config.get("goals", [])]
    keywords = {key: tuple(value) for key, value in _DEFAULT_KEYWORDS.items()}
    keywords.update({key: tuple(value) for key, value in (config.get("goal_keywords") or {}).items()})
    requested = tuple(keyword for goal in goals for keyword in keywords.get(goal, (goal,)))
    max_routes = max(1, int(config.get("max_routes", 5)))
    weekly_minutes = max(0, int(config.get("weekly_minutes", 0)))
    routes = []
    max_courses = max((int(route.get("course_count") or 0) for route in catalog.get("routes", [])), default=1)
    for route in catalog.get("routes", []):
        name = str(route.get("name", ""))
        haystack = _normalized(name)
        hits = sorted({keyword for keyword in requested if _normalized(keyword) in haystack})
        match_score = len(hits) / len(set(requested)) if requested else 0.0
        progress = float(route.get("progress_percent") or 0)
        course_count = int(route.get("course_count") or 0)
        cost_score = 1.0 - min(1.0, course_count / max_courses)
        score = round(match_score * 0.8 + (progress / 100) * 0.1 + cost_score * 0.1, 4)
        routes.append({
            "name": name,
            "url": route.get("url"),
            "kind": route.get("kind"),
            "course_count": course_count,
            "progress_percent": progress,
            "matched_keywords": hits,
            "score": score,
            "estimated_minutes": None,
            "reason": "coincidencia determinista de objetivos" if hits else "cobertura secundaria",
        })
    routes.sort(key=lambda item: (-item["score"], item["course_count"], item["name"].casefold()))
    selected = routes[:max_routes]
    remaining = weekly_minutes
    for route in selected:
        planned = min(remaining, route["course_count"] * int(config.get("minutes_per_course", 30)))
        route["planned_minutes"] = planned
        remaining -= planned
    return {
        "schema": "platzi-route-plan.v1",
        "goals": goals,
        "weekly_minutes": weekly_minutes,
        "max_routes": max_routes,
        "routes": selected,
        "remaining_weekly_minutes": remaining,
        "course_level_deduplication": "pending_course_catalog",
        "determinism": {"model_used": False, "ranking": "keyword_match+progress+estimated_cost"},
    }
