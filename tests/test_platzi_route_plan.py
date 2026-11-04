from pathlib import Path
import json

from academic_workspace.platzi_route_plan import build_route_plan


def test_route_plan_is_deterministic_and_prefers_goal_matches():
    catalog = {
        "routes": [
            {"name": "Data Analyst", "url": "u1", "course_count": 10, "progress_percent": 0},
            {"name": "Diseño UX", "url": "u2", "course_count": 5, "progress_percent": 0},
        ]
    }
    config = {"goals": ["data_science"], "weekly_minutes": 300, "max_routes": 3}

    first = build_route_plan(catalog, config)
    second = build_route_plan(catalog, config)

    assert first == second
    assert first["routes"][0]["name"] == "Data Analyst"
    assert first["routes"][0]["score"] > first["routes"][1]["score"]
