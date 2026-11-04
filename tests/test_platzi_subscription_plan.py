from academic_workspace.platzi_subscription_plan import build_subscription_plan


def test_subscription_plan_starts_with_shared_near_complete_priority_route():
    routes = [
        {"name": "Data Analyst", "url": "a", "course_count": 2, "progress_percent": 50},
        {"name": "Machine Learning", "url": "b", "course_count": 4, "progress_percent": 0},
    ]
    catalog = {"routes": [
        {"route_url": "a", "courses": [{"url": "https://platzi.com/cursos/shared/"}, {"url": "https://platzi.com/cursos/a2/"}]},
        {"route_url": "b", "courses": [{"url": "https://platzi.com/cursos/shared/"}, {"url": "https://platzi.com/cursos/b2/"}]},
    ]}
    result = build_subscription_plan(routes, catalog, weeks=2)
    assert result["weekly_plan"][0]["course_url"].endswith("shared/")
    assert result["course_per_week"] == 1


def test_fast_track_cadence_is_configurable():
    result = build_subscription_plan([], {"routes": []}, weeks=16, max_courses_per_week=10)
    assert result["course_per_week"] == 10
    assert result["cadence_policy"]["ia"] == 10
