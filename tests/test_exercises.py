def test_list_exercises_empty(client, auth_headers):
    resp = client.get("/api/v1/exercises/", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_and_get_exercise(client, auth_headers):
    resp = client.post("/api/v1/exercises/", headers=auth_headers, json={
        "name": "Unique Test Exercise",
        "category": "strength",
        "muscle_group": "chest",
        "equipment": "barbell",
        "description": "A test exercise",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Unique Test Exercise"

    ex_id = data["id"]
    get_resp = client.get(f"/api/v1/exercises/{ex_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == ex_id


def test_create_duplicate_exercise(client, auth_headers, sample_exercise):
    resp = client.post("/api/v1/exercises/", headers=auth_headers, json={
        "name": sample_exercise.name,
        "category": "strength",
        "muscle_group": "legs",
    })
    assert resp.status_code == 400


def test_filter_exercises_by_muscle_group(client, auth_headers, sample_exercise):
    resp = client.get("/api/v1/exercises/?muscle_group=legs", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert all(ex["muscle_group"] == "legs" for ex in data)


def test_search_exercises_by_name(client, auth_headers, sample_exercise):
    resp = client.get(f"/api/v1/exercises/?search=Squat", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert any("Squat" in ex["name"] for ex in data)


def test_get_exercise_not_found(client, auth_headers):
    resp = client.get("/api/v1/exercises/999999", headers=auth_headers)
    assert resp.status_code == 404
