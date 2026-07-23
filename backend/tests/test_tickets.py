"""
Ticket tests – covers basic lookup and check-in via DynamoDB.
"""
from fastapi.testclient import TestClient
from decimal import Decimal
from datetime import datetime, timedelta


def _create_order(client, sample_event):
    event_id = sample_event["id"]
    tt_id = sample_event["ticket_types"][0]["id"]
    resp = client.post("/orders", json={
        "event_id": event_id,
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


def test_checkin_scan(client: TestClient, sample_event, organizer_headers):
    order = _create_order(client, sample_event)
    ticket_code = order["items"][0]["tickets"][0]["ticket_code"]
    resp = client.post("/checkin/scan", json={"ticket_code": ticket_code}, headers=organizer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert "Check-in successful" in data["message"]


def test_double_checkin_rejected(client: TestClient, sample_event, organizer_headers):
    order = _create_order(client, sample_event)
    ticket_code = order["items"][0]["tickets"][0]["ticket_code"]
    # First check-in
    client.post("/checkin/scan", json={"ticket_code": ticket_code}, headers=organizer_headers)
    # Second check-in should fail
    resp = client.post("/checkin/scan", json={"ticket_code": ticket_code}, headers=organizer_headers)
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


def test_ticket_qr_generation(client: TestClient):
    from app.core.qr import generate_qr_code
    long_code = "TKT-VERY-LONG-PAYLOAD-WITH-JSON-DATA-OR-UUID-1234567890-ABCDEF-HIGKLMNOPQRSTUVWXYZ"
    qr_bytes = generate_qr_code(long_code)
    assert qr_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    resp = client.get(f"/tickets/{long_code}/qr")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content.startswith(b"\x89PNG\r\n\x1a\n")
