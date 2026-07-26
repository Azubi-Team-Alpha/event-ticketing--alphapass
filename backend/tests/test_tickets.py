"""
Ticket tests – covers basic lookup, PDF generation, attendee roster PDF export, and check-in via DynamoDB.
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


def test_attendee_pdf_export(client: TestClient, sample_event, organizer_headers):
    order = _create_order(client, sample_event)
    event_id = sample_event["id"]
    resp = client.get(f"/organizer/events/{event_id}/attendees?export=pdf", headers=organizer_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF-")


def test_resale_purchase_transfers_and_allows_checkin(client, mock_dynamodb_tables, organizer_headers):
    """Verify that after resale purchase, ticket details transfer to buyer and check-in succeeds."""
    from app.db.dynamodb import dynamodb_helper

    # 1. Create a ticket
    t_id = "tkt-resale-verify-1"
    t_code = "AP-RESALE-VERIFY-001"
    t_data = {
        "TicketID": t_id,
        "id": t_id,
        "ticket_code": t_code,
        "attendee_name": "Original Seller",
        "attendee_email": "seller@example.com",
        "status": "active",
        "is_used": False,
    }
    dynamodb_helper.create_ticket(t_id, t_data)

    # 2. List ticket for resale
    l_id = "listing-verify-001"
    dynamodb_helper.create_resale_listing(l_id, {
        "ListingID": l_id,
        "id": l_id,
        "ticket_id": t_id,
        "ticket_code": t_code,
        "seller_name": "Original Seller",
        "seller_email": "seller@example.com",
        "asking_price": 50.00,
        "status": "active",
    })

    # 3. Buyer purchases resale ticket
    buy_resp = client.post(f"/resale/{l_id}/purchase", json={
        "buyer_name": "New Buyer",
        "buyer_email": "buyer@example.com",
    })
    assert buy_resp.status_code == 201

    # 4. Verify ticket was updated to buyer details
    updated_t = dynamodb_helper.get_ticket(t_id)
    assert updated_t["attendee_name"] == "New Buyer"
    assert updated_t["attendee_email"] == "buyer@example.com"
    assert updated_t["status"] == "active"
    assert updated_t["is_used"] is False

    # 5. Verify check-in scan succeeds for the buyer
    scan_resp = client.post(f"/checkin/scan", json={"ticket_code": t_code}, headers=organizer_headers)
    assert scan_resp.status_code == 200
    scan_json = scan_resp.json()
    assert scan_json["valid"] is True
    assert scan_json["attendee_name"] == "New Buyer"

