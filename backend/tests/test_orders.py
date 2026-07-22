"""Order (guest checkout) tests."""
import uuid
import pytest
from fastapi.testclient import TestClient
from app.db.dynamodb import dynamodb_helper


def _make_order(client, sample_event):
    event_id = sample_event["id"]
    tt_id = sample_event["ticket_types"][0]["id"]
    return client.post("/orders", json={
        "event_id": event_id,
        "guest_name": "Alice Smith",
        "guest_email": "alice@test.com",
        "guest_phone": "+1-555-1234",
        "items": [{"ticket_type_id": tt_id, "quantity": 2}],
    })


def test_create_order_guest(client: TestClient, sample_event):
    resp = _make_order(client, sample_event)
    assert resp.status_code == 201
    data = resp.json()
    assert data["guest_email"] == "alice@test.com"
    assert data["total_tickets"] == 2
    assert data["status"] == "confirmed"


def test_order_lookup(client: TestClient, sample_event):
    create_resp = _make_order(client, sample_event)
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]

    resp = client.post("/orders/lookup", json={
        "order_id": order_id,
        "guest_email": "alice@test.com",
    })
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id


def test_order_wrong_email_lookup(client: TestClient, sample_event):
    create_resp = _make_order(client, sample_event)
    order_id = create_resp.json()["id"]
    resp = client.post("/orders/lookup", json={
        "order_id": order_id,
        "guest_email": "wrong@test.com",
    })
    assert resp.status_code == 404


def test_order_oversell_rejected(client: TestClient, sample_event):
    event_id = sample_event["id"]
    tt_id = sample_event["ticket_types"][0]["id"]
    resp = client.post("/orders", json={
        "event_id": event_id,
        "guest_name": "Bob",
        "guest_email": "bob@test.com",
        "items": [{"ticket_type_id": tt_id, "quantity": 999}],  # exceeds quantity
    })
    assert resp.status_code == 400


def test_order_purchase_limit_rejected(client: TestClient, sample_event):
    event_id = sample_event["id"]
    tt_id = sample_event["ticket_types"][0]["id"]
    resp = client.post("/orders", json={
        "event_id": event_id,
        "guest_name": "Charlie",
        "guest_email": "charlie@test.com",
        "items": [{"ticket_type_id": tt_id, "quantity": 6}],  # exceeds limit of 5
    })
    assert resp.status_code == 400


def test_order_cancel(client: TestClient, sample_event):
    create_resp = _make_order(client, sample_event)
    order_id = create_resp.json()["id"]
    resp = client.put(f"/orders/{order_id}/cancel")
    assert resp.status_code == 200


def test_bulk_order_mixed_types(client: TestClient, sample_event):
    event_id = sample_event["id"]
    vip_id = str(uuid.uuid4())
    
    tts = sample_event.get("ticket_types", [])
    tts.append({
        "id": vip_id,
        "name": "VIP",
        "price": "150.00",
        "quantity": 20,
        "quantity_sold": 0,
        "purchase_limit": 5,
        "min_purchase": 1,
        "is_active": True,
    })
    dynamodb_helper.update_event(event_id, {"ticket_types": tts})

    tt_id = tts[0]["id"]
    resp = client.post("/orders", json={
        "event_id": event_id,
        "guest_name": "Group Leader",
        "guest_email": "group@test.com",
        "items": [
            {"ticket_type_id": tt_id, "quantity": 3},
            {"ticket_type_id": vip_id, "quantity": 2},
        ],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_tickets"] == 5
    assert len(data["items"]) == 2
