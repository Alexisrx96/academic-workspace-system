from academic_workspace.platzi_global_plan import build_global_route_order


def test_global_order_prioritizes_route_with_shared_courses():
    routes = [
        {"name": "A", "url": "a", "course_count": 3, "progress_percent": 0},
        {"name": "B", "url": "b", "course_count": 3, "progress_percent": 0},
    ]
    catalog = {"routes": [
        {"route_url": "a", "courses": [{"url": "c1"}, {"url": "c2"}, {"url": "c3"}]},
        {"route_url": "b", "courses": [{"url": "c1"}, {"url": "c2"}, {"url": "c4"}]},
    ]}

    result = build_global_route_order(routes, catalog, weekly_minutes=180)

    assert result["schema"] == "platzi-global-route-plan.v1"
    assert result["routes"][0]["incremental_courses"] == 3
    assert result["routes"][1]["incremental_courses"] == 1
    assert result["unique_courses_total"] == 4
