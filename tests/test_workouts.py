import pytest
from datetime import datetime, timedelta


def test_create_workout_no_exercises(client, auth_headers):
    resp = client.post("/api/v1/workouts/", headers=auth_headers, json={
        "title": "Morning Session",
        "notes": "Leg day",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["message"] == "Workout created successfully"
    assert "workout_id" in data


def test_create_workout_with_exercise(client, auth_headers, sample_exercise):
    resp = client.post("/api/v1/workouts/", headers=auth_headers, json={
        "title": "Squat Day",
        "exercises": [
            {"exercise_id": sample_exercise.id, "sets": 4, "reps": 8, "weight_kg": 100.0}
        ],
    })
    assert resp.status_code == 201
    assert resp.json()["message"] == "Workout created successfully"


def test_create_workout_invalid_exercise_id(client, auth_headers):
    resp = client.post("/api/v1/workouts/", headers=auth_headers, json={
        "title": "Bad Workout",
        "exercises": [{"exercise_id": 99999, "sets": 3, "reps": 10}],
    })
    assert resp.status_code == 404


def test_list_workouts(client, auth_headers):
    client.post("/api/v1/workouts/", headers=auth_headers, json={"title": "Workout A"})
    client.post("/api/v1/workouts/", headers=auth_headers, json={"title": "Workout B"})
    resp = client.get("/api/v1/workouts/", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_get_workout(client, auth_headers):
    create = client.post("/api/v1/workouts/", headers=auth_headers, json={"title": "Get Me"})
    wid = create.json()["workout_id"]
    resp = client.get(f"/api/v1/workouts/{wid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == wid


def test_get_workout_not_found(client, auth_headers):
    resp = client.get("/api/v1/workouts/999999", headers=auth_headers)
    assert resp.status_code == 404


def test_update_workout_put(client, auth_headers):
    create = client.post("/api/v1/workouts/", headers=auth_headers, json={"title": "Old"})
    wid = create.json()["workout_id"]
    resp = client.put(f"/api/v1/workouts/{wid}", headers=auth_headers, json={
        "title": "New Title",
        "status": "completed",
    })
    assert resp.status_code == 200
    assert resp.json()["message"] == "Workout updated successfully"


def test_delete_workout(client, auth_headers):
    create = client.post("/api/v1/workouts/", headers=auth_headers, json={"title": "Delete Me"})
    wid = create.json()["workout_id"]
    resp = client.delete(f"/api/v1/workouts/{wid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Workout deleted successfully"
    assert client.get(f"/api/v1/workouts/{wid}", headers=auth_headers).status_code == 404


def test_scheduled_workouts(client, auth_headers):
    future = (datetime.utcnow() + timedelta(days=3)).isoformat()
    client.post("/api/v1/workouts/", headers=auth_headers, json={
        "title": "Future Session",
        "scheduled_at": future,
    })
    resp = client.get("/api/v1/workouts/scheduled", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_workout_isolation(client, db):
    resp_a = client.post("/api/v1/auth/register", json={
        "email": "usera@example.com", "username": "usera", "password": "password123"
    })
    headers_a = {"Authorization": f"Bearer {resp_a.json()['access_token']}"}

    resp_b = client.post("/api/v1/auth/register", json={
        "email": "userb@example.com", "username": "userb", "password": "password123"
    })
    headers_b = {"Authorization": f"Bearer {resp_b.json()['access_token']}"}

    wk = client.post("/api/v1/workouts/", headers=headers_a, json={"title": "Private"})
    wid = wk.json()["workout_id"]

    resp = client.get(f"/api/v1/workouts/{wid}", headers=headers_b)
    assert resp.status_code == 404


def test_list_workouts_unauthenticated(client):
    assert client.get("/api/v1/workouts/").status_code == 401
