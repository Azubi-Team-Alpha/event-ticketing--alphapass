"""Tests for new Ticket Hub features: group discounts, refunds, resale approval, configs, custom admin creation, CSV export."""
import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from app.models.models import (
    Event, EventStatus, TicketType, Order, OrderStatus, Ticket, TicketStatus,
    ResaleListing, ResaleStatus, PlatformSettings, Admin
)
from app.core.security import hash_password

# 1. Test Group Discount
def test_group_discount_applied(client, db, organizer_user, category):
    # Create an event with group discount threshold=3, percent=10.00
    event = Event(
        organizer_id=organizer_user.id,
        category_id=category.id,
        title="Group Discount Event",
        description="Event description",
        venue_name="Venue",
        starts_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=2),
        ends_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=2, hours=3),
        status=EventStatus.published,
        group_discount_threshold=3,
        group_discount_percent=Decimal("10.00"),
    )
    db.add(event)
    db.flush()
    tt = TicketType(
        event_id=event.id,
        name="Group Ticket",
        price=Decimal("100.00"),
        quantity=50,
        purchase_limit=10,
        min_purchase=1,
    )
    db.add(tt)
    db.commit()

    # Place order with 2 tickets (under threshold)
    payload_under = {
        "event_id": event.id,
        "items": [{"ticket_type_id": tt.id, "quantity": 2}],
        "guest_name": "Under threshold",
        "guest_email": "under@test.com",
        "payment_method": "card",
        "payment_reference": "ref_under"
    }
    r1 = client.post("/orders", json=payload_under)
    assert r1.status_code == 201
    o1 = r1.json()
    # Subtotal = 200, discount = 0, platform_fee = 5% of 200 = 10, total = 210
    assert float(o1["subtotal"]) == 200.0
    assert float(o1["discount_amount"]) == 0.0
    assert float(o1["total_amount"]) == 210.0

    # Place order with 3 tickets (meets threshold)
    payload_meets = {
        "event_id": event.id,
        "items": [{"ticket_type_id": tt.id, "quantity": 3}],
        "guest_name": "Meets threshold",
        "guest_email": "meets@test.com",
        "payment_method": "card",
        "payment_reference": "ref_meets"
    }
    r2 = client.post("/orders", json=payload_meets)
    assert r2.status_code == 201
    o2 = r2.json()
    # Subtotal = 300, group discount = 10% of 300 = 30, discount = 30.00
    assert float(o2["subtotal"]) == 300.0
    assert float(o2["discount_amount"]) == 30.0
    # Taxable = 270, platform_fee = 5% of 270 = 13.50, total = 283.50
    assert float(o2["total_amount"]) == 283.50


# 2. Test Event Archiving
def test_archive_event(client, sample_event, organizer_headers):
    # Archive the event
    r = client.post(f"/events/organizer/{sample_event.id}/archive", headers=organizer_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "archived"


# 3. Test Event Search Filters
def test_event_search_filters(client, db, organizer_user, category):
    # Clean out events
    db.query(Event).delete()
    db.commit()

    e1 = Event(
        organizer_id=organizer_user.id, category_id=category.id,
        title="Cheap Event", venue_name="Venue 1", city="Accra",
        starts_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=5),
        ends_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=5, hours=2),
        status=EventStatus.published
    )
    db.add(e1)
    db.flush()
    db.add(TicketType(event_id=e1.id, name="General", price=Decimal("15.00"), quantity=100))

    e2 = Event(
        organizer_id=organizer_user.id, category_id=category.id,
        title="Expensive Event", venue_name="Venue 2", city="Lagos",
        starts_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=15),
        ends_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=15, hours=2),
        status=EventStatus.published
    )
    db.add(e2)
    db.flush()
    db.add(TicketType(event_id=e2.id, name="VIP", price=Decimal("150.00"), quantity=50))
    db.commit()

    # Search for min_price=100
    r = client.get("/events?min_price=100")
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Expensive Event"

    # Search for max_price=50
    r2 = client.get("/events?max_price=50")
    assert r2.status_code == 200
    data2 = r2.json()
    assert len(data2["items"]) == 1
    assert data2["items"][0]["title"] == "Cheap Event"

    # Search by date_from and date_to
    date_from = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=10)).isoformat()
    r3 = client.get(f"/events?date_from={date_from}")
    assert r3.status_code == 200
    data3 = r3.json()
    assert len(data3["items"]) == 1
    assert data3["items"][0]["title"] == "Expensive Event"


# 4. Test Platform Config endpoints
def test_platform_configs(client, admin_headers):
    # Get all configs
    r = client.get("/admin/config", headers=admin_headers)
    assert r.status_code == 200

    # Put a setting
    r2 = client.put("/admin/config/test_setting?value=true", headers=admin_headers)
    assert r2.status_code == 200
    assert r2.json()["message"] == "Config test_setting updated to: true"

    # Get configs again to verify
    r3 = client.get("/admin/config", headers=admin_headers)
    assert r3.status_code == 200
    configs = r3.json()
    setting = next((c for c in configs if c["key"] == "test_setting"), None)
    assert setting is not None
    assert setting["value"] == "true"


# 5. Test Super Admin creates Admin directly
def test_create_admin(client, admin_headers):
    payload = {
        "email": "newadmin@test.com",
        "full_name": "New Admin",
        "password": "Password123",
        "is_super": False
    }
    r = client.post("/admin/create-admin", json=payload, headers=admin_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "newadmin@test.com"
    assert data["full_name"] == "New Admin"
    assert data["is_super"] is False


# 6. Test Resale Approvals
def test_resale_approval_flow(client, db, sample_event, admin_headers):
    # Set require_resale_approval to true
    setting = PlatformSettings(key="require_resale_approval", value="true")
    db.add(setting)
    db.commit()

    # Buy a ticket to resell
    payload = {
        "event_id": sample_event.id,
        "items": [{"ticket_type_id": sample_event.ticket_types[0].id, "quantity": 1}],
        "guest_name": "Seller",
        "guest_email": "seller@test.com",
        "payment_method": "card",
        "payment_reference": "ref_resale"
    }
    r = client.post("/orders", json=payload)
    order = r.json()
    ticket_code = order["items"][0]["tickets"][0]["ticket_code"]

    # List ticket for resale
    list_payload = {
        "seller_name": "Seller",
        "seller_email": "seller@test.com",
        "asking_price": 55.00
    }
    r_list = client.post(f"/resale/tickets/{ticket_code}", json=list_payload)
    assert r_list.status_code == 201
    listing = r_list.json()
    assert listing["status"] == "pending"

    # Admin lists pending resales
    r_admin_list = client.get("/admin/resale?status=pending", headers=admin_headers)
    assert r_admin_list.status_code == 200
    pending_items = r_admin_list.json()["items"]
    assert len(pending_items) == 1
    assert pending_items[0]["id"] == listing["id"]

    # Admin approves resale
    r_approve = client.put(f"/admin/resale/{listing['id']}/approve", json={"approved": True}, headers=admin_headers)
    assert r_approve.status_code == 200

    # Verify listing is now active
    db.expire_all()
    db_listing = db.query(ResaleListing).filter(ResaleListing.id == listing["id"]).first()
    assert db_listing.status == ResaleStatus.active


# 7. Test Refund Flows
def test_refund_flow(client, db, sample_event, admin_headers):
    # Buy a ticket
    payload = {
        "event_id": sample_event.id,
        "items": [{"ticket_type_id": sample_event.ticket_types[0].id, "quantity": 1}],
        "guest_name": "Refunder",
        "guest_email": "refunder@test.com",
        "payment_method": "card",
        "payment_reference": "ref_refund"
    }
    r = client.post("/orders", json=payload)
    order = r.json()

    # Request refund
    r_req = client.post(f"/orders/{order['id']}/refund-request", json={
        "guest_email": "refunder@test.com",
        "reason": "Illness"
    })
    assert r_req.status_code == 200

    # Admin lists pending refunds
    r_admin_list = client.get("/admin/refunds", headers=admin_headers)
    assert r_admin_list.status_code == 200
    refunds = r_admin_list.json()["items"]
    assert len(refunds) == 1
    assert refunds[0]["id"] == order["id"]

    # Admin approves refund
    r_approve = client.put(f"/admin/orders/{order['id']}/refund", json={"approved": True, "rejection_reason": ""}, headers=admin_headers)
    assert r_approve.status_code == 200

    # Verify order is refunded and tickets cancelled
    db.expire_all()
    db_order = db.query(Order).filter(Order.id == order["id"]).first()
    assert db_order.status == OrderStatus.refunded
    assert db_order.items[0].tickets[0].status == TicketStatus.cancelled


# 8. Test Organizer Attendees CSV Export
def test_organizer_attendee_csv_export(client, db, sample_event, organizer_headers):
    # Purchase a ticket to ensure there are attendees
    payload = {
        "event_id": sample_event.id,
        "items": [{"ticket_type_id": sample_event.ticket_types[0].id, "quantity": 1}],
        "guest_name": "CSV Attendee",
        "guest_email": "csv@test.com",
        "payment_method": "card",
        "payment_reference": "ref_csv"
    }
    client.post("/orders", json=payload)

    # Export attendees as CSV
    r = client.get(f"/organizer/events/{sample_event.id}/attendees?format=csv", headers=organizer_headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "text/csv; charset=utf-8"
    content = r.text
    assert "Ticket Code" in content
    assert "CSV Attendee" in content
    assert "csv@test.com" in content
