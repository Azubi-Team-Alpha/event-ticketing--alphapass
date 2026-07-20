"""
Ticket tests – covers basic lookup and check-in via the new models.
The old test_tickets.py assumed legacy Registration/User models.
"""
from fastapi.testclient import TestClient
from decimal import Decimal
from datetime import datetime, timedelta


def _create_order(client, sample_event):
    tt_id = sample_event.ticket_types[0].id
    resp = client.post("/orders", json={
        "event_id": sample_event.id,
        "guest_name": "Dave",
        "guest_email": "dave@test.com",
        "items": [{"ticket_type_id": tt_id, "quantity": 1}],
    })
    assert resp.status_code == 201
    return resp.json()


def test_ticket_lookup_by_code(client: TestClient, sample_event):
    order = _create_order(client, sample_event)
    ticket_code = order["items"][0]["tickets"][0]["ticket_code"]
    resp = client.get(f"/tickets/{ticket_code}")
    assert resp.status_code == 200
    assert resp.json()["ticket_code"] == ticket_code


def test_checkin_scan(client: TestClient, sample_event):
    order = _create_order(client, sample_event)
    ticket_code = order["items"][0]["tickets"][0]["ticket_code"]
    resp = client.post("/checkin/scan", json={"ticket_code": ticket_code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert "Check-in successful" in data["message"]


def test_double_checkin_rejected(client: TestClient, sample_event):
    order = _create_order(client, sample_event)
    ticket_code = order["items"][0]["tickets"][0]["ticket_code"]
    # First check-in
    client.post("/checkin/scan", json={"ticket_code": ticket_code})
    # Second check-in should fail
    resp = client.post("/checkin/scan", json={"ticket_code": ticket_code})
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


def test_invalid_ticket_code(client: TestClient):
    resp = client.get("/tickets/NONEXISTENT-CODE-XYZ")
    assert resp.status_code == 404


def test_ticket_pdf_download(client: TestClient, sample_event):
    order = _create_order(client, sample_event)
    ticket_code = order["items"][0]["tickets"][0]["ticket_code"]
    resp = client.get(f"/tickets/{ticket_code}/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF-")

