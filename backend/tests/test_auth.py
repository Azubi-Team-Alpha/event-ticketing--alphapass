"""Auth endpoint tests."""
import pytest
from fastapi.testclient import TestClient


def test_admin_signup(client: TestClient):
    resp = client.post("/auth/admin/signup", json={
        "email": "newadmin@test.com",
        "full_name": "New Admin",
        "password": "securepass123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "newadmin@test.com"
    assert data["is_super"] is True   # first admin is super


def test_admin_login(client: TestClient, admin_user):
    resp = client.post("/auth/admin/login", json={
        "email": "admin@test.com",
        "password": "adminpass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "admin"


def test_admin_login_wrong_password(client: TestClient, admin_user):
    resp = client.post("/auth/admin/login", json={
        "email": "admin@test.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


def test_admin_me(client: TestClient, admin_headers, admin_user):
    resp = client.get("/auth/admin/me", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@test.com"


def test_organizer_signup(client: TestClient):
    resp = client.post("/auth/organizer/signup", json={
        "email": "neworg@test.com",
        "full_name": "New Organizer",
        "password": "orgpass123",
        "business_name": "Cool Events",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "neworg@test.com"
    assert data["status"] == "pending"


def test_organizer_login(client: TestClient, organizer_user):
    resp = client.post("/auth/organizer/login", json={
        "email": "org@test.com",
        "password": "orgpass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "organizer"


def test_organizer_me(client: TestClient, organizer_headers):
    resp = client.get("/auth/organizer/me", headers=organizer_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "org@test.com"


def test_duplicate_organizer_email(client: TestClient, organizer_user):
    resp = client.post("/auth/organizer/signup", json={
        "email": "org@test.com",
        "full_name": "Duplicate",
        "password": "somepass123",
    })
    assert resp.status_code == 400


def test_password_too_short(client: TestClient):
    resp = client.post("/auth/organizer/signup", json={
        "email": "short@test.com",
        "full_name": "Short",
        "password": "abc",
    })
    assert resp.status_code == 422
