from academic_workspace.platzi_path import build_optimal_platzi_path


def test_platzi_path_respects_prerequisites_and_goal_skills():
    catalog = {
        "courses": [
            {"id": "advanced", "name": "Avanzado", "skills": ["apis"], "duration_minutes": 120, "prerequisites": ["basics"]},
            {"id": "basics", "name": "Fundamentos", "skills": ["basics"], "duration_minutes": 90, "prerequisites": []},
        ],
        "routes": [{"id": "r1", "name": "Backend", "course_ids": ["advanced", "basics"]}],
    }

    result = build_optimal_platzi_path(catalog, goals=["apis"], weekly_minutes=120)

    assert result["schema"] == "platzi-learning-path.v1"
    assert [item["course_id"] for item in result["steps"]] == ["basics", "advanced"]
    assert result["steps"][0]["reason"]


def test_platzi_path_respects_capacity():
    catalog = {"courses": [{"id": "c1", "name": "Curso", "skills": ["python"], "duration_minutes": 240, "prerequisites": []}]}

    result = build_optimal_platzi_path(catalog, goals=["python"], weekly_minutes=120)

    assert result["weekly_minutes"] == 120
    assert result["steps"][0]["planned_minutes"] == 120
    assert result["steps"][0]["remaining_minutes"] == 120


def test_platzi_path_studies_shared_trunk_once_for_multiple_routes():
    catalog = {
        "courses": [
            {"id": "common", "name": "Tronco común", "skills": ["base"], "duration_minutes": 60, "prerequisites": []},
            {"id": "data", "name": "Ruta datos", "skills": ["data"], "duration_minutes": 100, "prerequisites": ["common"]},
            {"id": "web", "name": "Ruta web", "skills": ["web"], "duration_minutes": 100, "prerequisites": ["common"]},
        ],
        "routes": [
            {"id": "r-data", "name": "Datos", "course_ids": ["common", "data"]},
            {"id": "r-web", "name": "Web", "course_ids": ["common", "web"]},
        ],
    }

    result = build_optimal_platzi_path(catalog, goals=["data", "web"], weekly_minutes=260, target_routes=["r-data", "r-web"])

    assert [item["course_id"] for item in result["steps"]] == ["common", "data", "web"]
    assert result["common_trunk"] == ["common"]
    assert result["routes_covered"] == ["Datos", "Web"]
    assert result["estimated_total_minutes"] == 260
