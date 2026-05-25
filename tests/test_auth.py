import pytest


def test_register_success(client):
    resp = client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "username": "newuser",
        "password": "password123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["message"] == "User registered successfully"
    assert "user_id" in data


def test_register_duplicate_email(client, registered_user):
    resp = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "other",
        "password": "password123",
    })
    assert resp.status_code == 400


def test_register_duplicate_username(client, registered_user):
    resp = client.post("/api/v1/auth/register", json={
        "email": "other@example.com",
        "username": "testuser",
        "password": "password123",
    })
    assert resp.status_code == 400


def test_register_weak_password(client):
    resp = client.post("/api/v1/auth/register", json={
        "email": "weak@example.com",
        "username": "weakuser",
        "password": "short",
    })
    assert resp.status_code == 422


def test_login_success(client, registered_user):
    resp = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "strongpassword123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client, registered_user):
    resp = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


def test_login_unknown_email(client):
    resp = client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "password123",
    })
    assert resp.status_code == 401


def test_me_authenticated(client, auth_headers):
    resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "testuser"


def test_me_unauthenticated(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_logout(client, registered_user, auth_headers):
    # Should succeed
    resp = client.post("/api/v1/auth/logout", headers=auth_headers)
    assert resp.status_code == 200
    assert "logged out" in resp.json()["message"].lower()
