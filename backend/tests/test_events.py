"""Event endpoint tests."""
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient


FUTURE_EVENT = {
    "title": "New Event 2026",
    "description": "A great event",
    "venue_name": "Test Hall",
    "city": "Accra",
    "country": "Ghana",
    "starts_at": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
    "ends_at": (datetime.now(timezone.utc) + timedelta(days=10, hours=4)).isoformat(),
}


def test_list_events_public(client: TestClient, sample_event):
    resp = client.get("/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(e["title"] == "Test Conference 2026" for e in data["items"])


def test_get_event_detail(client: TestClient, sample_event):
    event_id = sample_event["id"]
    resp = client.get(f"/events/{event_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == event_id
    assert len(data["ticket_types"]) == 1


def test_get_nonexistent_event(client: TestClient):
    resp = client.get("/events/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_organizer_create_event(client: TestClient, organizer_headers, category):
    payload = {**FUTURE_EVENT, "category_id": category["id"]}
    resp = client.post("/events/organizer", json=payload, headers=organizer_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "New Event 2026"
    assert data["status"] == "draft"


def test_organizer_create_event_no_auth(client: TestClient):
    resp = client.post("/events/organizer", json=FUTURE_EVENT)
    assert resp.status_code in (401, 403)


def test_organizer_add_ticket_type(client: TestClient, organizer_headers, sample_event):
    event_id = sample_event["id"]
    resp = client.post(
        f"/events/organizer/{event_id}/ticket-types",
        json={"name": "VIP", "price": "199.00", "quantity": 20, "purchase_limit": 2},
        headers=organizer_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "VIP"
    assert data["quantity"] == 20


def test_organizer_publish_event(client: TestClient, organizer_headers, sample_event):
    event_id = sample_event["id"]
    resp = client.post(f"/events/organizer/{event_id}/publish", headers=organizer_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"


def test_list_categories(client: TestClient, category):
    resp = client.get("/events/categories")
    assert resp.status_code == 200
    cats = resp.json()
    assert any(c["slug"] == "technology" for c in cats)


def test_search_events(client: TestClient, sample_event):
    resp = client.get("/events?search=Conference")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
