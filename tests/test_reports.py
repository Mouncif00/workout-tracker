def test_progress_report(client, auth_headers):
    resp = client.get("/api/v1/reports/progress", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_workouts" in data
    assert "completed_workouts" in data
    assert "pending_workouts" in data
    assert "cancelled_workouts" in data


def test_monthly_report_default(client, auth_headers):
    resp = client.get("/api/v1/reports/monthly", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "month" in data
    assert "workouts_completed" in data
    assert "average_intensity" in data


def test_monthly_report_specific_month(client, auth_headers):
    resp = client.get("/api/v1/reports/monthly?year=2025&month=1", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["month"] == "January 2025"


def test_exercises_report_empty(client, auth_headers):
    resp = client.get("/api/v1/reports/exercises", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_exercises_report_with_data(client, auth_headers, sample_exercise):
    # Create and complete a workout with an exercise
    create = client.post("/api/v1/workouts/", headers=auth_headers, json={
        "title": "Report Test",
        "exercises": [{"exercise_id": sample_exercise.id, "sets": 3, "reps": 10, "weight_kg": 50.0}],
    })
    wid = create.json()["workout_id"]
    client.put(f"/api/v1/workouts/{wid}", headers=auth_headers, json={"status": "completed"})

    resp = client.get("/api/v1/reports/exercises", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert "exercise_name" in data[0]
    assert "usage_count" in data[0]


def test_reports_require_auth(client):
    assert client.get("/api/v1/reports/progress").status_code == 401
    assert client.get("/api/v1/reports/monthly").status_code == 401
    assert client.get("/api/v1/reports/exercises").status_code == 401
