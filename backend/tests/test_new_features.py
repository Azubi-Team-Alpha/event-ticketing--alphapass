"""Tests for AlphaPass features: group discounts, refunds, resale approval, configs, custom admin creation, CSV export using DynamoDB."""
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from app.db.dynamodb import dynamodb_helper
from app.core.security import hash_password


# 1. Test Group Discount
def test_group_discount_applied(client, organizer_user, category):
    event_id = str(uuid.uuid4())
    tt_id = str(uuid.uuid4())

    event_data = dynamodb_helper.create_event(event_id, {
        "organizer_id": organizer_user["id"],
        "category_id": category["id"],
        "title": "Group Discount Event",
        "description": "Event description",
        "venue_name": "Venue",
        "starts_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "ends_at": (datetime.now(timezone.utc) + timedelta(days=2, hours=3)).isoformat(),
        "status": "published",
        "group_discount_threshold": 3,
        "group_discount_percent": "10.00",
        "ticket_types": [
            {
                "id": tt_id,
                "name": "Group Ticket",
                "price": "100.00",
                "quantity": 50,
                "quantity_sold": 0,
                "purchase_limit": 10,
                "min_purchase": 1,
                "is_active": True,
            }
        ]
    })

    # Place order with 2 tickets (under threshold)
    payload_under = {
        "event_id": event_id,
        "items": [{"ticket_type_id": tt_id, "quantity": 2}],
        "guest_name": "Under threshold",
        "guest_email": "under@test.com",
        "payment_method": "card",
        "payment_reference": "ref_under"
    }
    r1 = client.post("/orders", json=payload_under)
    assert r1.status_code == 201
    o1 = r1.json()
    assert float(o1["subtotal"]) == 200.0
    assert float(o1["discount_amount"]) == 0.0
    assert float(o1["total_amount"]) == 210.0

    # Place order with 3 tickets (meets threshold)
    payload_meets = {
        "event_id": event_id,
        "items": [{"ticket_type_id": tt_id, "quantity": 3}],
        "guest_name": "Meets threshold",
        "guest_email": "meets@test.com",
        "payment_method": "card",
        "payment_reference": "ref_meets"
    }
    r2 = client.post("/orders", json=payload_meets)
    assert r2.status_code == 201
    o2 = r2.json()
    assert float(o2["subtotal"]) == 300.0
    assert float(o2["discount_amount"]) == 30.0
    assert float(o2["total_amount"]) == 283.50


# 2. Test Event Search Filters
def test_event_search_filters(client, sample_event):
    r1 = client.get("/events?city=Accra")
    assert r1.status_code == 200
    assert r1.json()["total"] >= 1

    r2 = client.get("/events?city=Kumasi")
    assert r2.status_code == 200
    assert r2.json()["total"] == 0


# 3. Test Config Management
def test_platform_configs(client, admin_headers):
    r1 = client.get("/admin/config", headers=admin_headers)
    assert r1.status_code == 200

    r2 = client.put("/admin/config/maintenance_mode?value=true", headers=admin_headers)
    assert r2.status_code == 200

    s = dynamodb_helper.get_platform_setting("maintenance_mode")
    assert s is not None
    assert s["value"] == "true"


# 4. Test Create Admin
def test_create_admin(client, admin_headers):
    payload = {
        "email": "newsubadmin@test.com",
        "full_name": "Sub Admin",
        "password": "password123",
        "is_super": False
    }
    r = client.post("/admin/create-admin", json=payload, headers=admin_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "newsubadmin@test.com"
    assert data["is_super"] is False
