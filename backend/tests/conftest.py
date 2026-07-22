"""Test fixtures for AlphaPass backend with mocked DynamoDB via moto."""
import os
import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import boto3
from moto import mock_aws
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Set environment BEFORE importing app
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")
os.environ.setdefault("S3_BUCKET_NAME", "test-bucket")
os.environ.setdefault("SES_SENDER_EMAIL", "test@example.com")


@pytest.fixture(scope="function")
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function", autouse=True)
def mock_dynamodb_tables(aws_credentials):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        def create_gsi_table(name, pk, gsis=None):
            attr_defs = [{"AttributeName": pk, "AttributeType": "S"}]
            gsi_defs = []

            if gsis:
                for idx_name, g_pk in gsis:
                    if not any(a["AttributeName"] == g_pk for a in attr_defs):
                        attr_defs.append({"AttributeName": g_pk, "AttributeType": "S"})
                    gsi_defs.append({
                        "IndexName": idx_name,
                        "KeySchema": [{"AttributeName": g_pk, "KeyType": "HASH"}],
                        "Projection": {"ProjectionType": "ALL"}
                    })

            kwargs = {
                "TableName": name,
                "KeySchema": [{"AttributeName": pk, "KeyType": "HASH"}],
                "AttributeDefinitions": attr_defs,
                "BillingMode": "PAY_PER_REQUEST",
            }
            if gsi_defs:
                kwargs["GlobalSecondaryIndexes"] = gsi_defs

            dynamodb.create_table(**kwargs)

        create_gsi_table("alphapass-events-dev", "EventID", [("organizer_id-index", "organizer_id"), ("status-index", "status")])
        create_gsi_table("alphapass-registrations-dev", "RegistrationID")
        create_gsi_table("alphapass-organizers-dev", "OrganizerID", [("email-index", "email"), ("verification_token-index", "verification_token"), ("reset_token-index", "reset_token")])
        create_gsi_table("alphapass-admins-dev", "AdminID", [("email-index", "email")])
        create_gsi_table("alphapass-orders-dev", "OrderID", [("event_id-index", "event_id"), ("guest_email-index", "guest_email")])
        create_gsi_table("alphapass-tickets-dev", "TicketID", [("ticket_code-index", "ticket_code"), ("order_id-index", "order_id"), ("attendee_email-index", "attendee_email")])
        create_gsi_table("alphapass-promo-codes-dev", "Code", [("event_id-index", "event_id")])
        create_gsi_table("alphapass-resale-listings-dev", "ListingID", [("ticket_id-index", "ticket_id"), ("status-index", "status")])
        create_gsi_table("alphapass-transfers-dev", "TransferID", [("ticket_id-index", "ticket_id")])
        create_gsi_table("alphapass-payouts-dev", "PayoutID", [("organizer_id-index", "organizer_id")])
        create_gsi_table("alphapass-platform-settings-dev", "SettingKey")
        create_gsi_table("alphapass-audit-logs-dev", "LogID")
        create_gsi_table("alphapass-event-categories-dev", "CategoryID")

        yield dynamodb


from app.main import app
from app.db.dynamodb import dynamodb_helper
from app.core.security import hash_password, create_access_token


@pytest.fixture
def client():
    return TestClient(app)


# ── Admin fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def admin_user():
    admin_id = str(uuid.uuid4())
    admin_data = dynamodb_helper.create_admin(admin_id, {
        "email": "admin@test.com",
        "full_name": "Test Admin",
        "password_hash": hash_password("adminpass123"),
        "is_super": True,
        "is_active": True,
        "email_verified": True,
    })
    admin_data["id"] = admin_id
    return admin_data


@pytest.fixture
def admin_token(admin_user):
    return create_access_token(admin_user["id"], role="admin")


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ── Organizer fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def organizer_user():
    org_id = str(uuid.uuid4())
    org_data = dynamodb_helper.create_organizer(org_id, {
        "email": "org@test.com",
        "full_name": "Test Organizer",
        "password_hash": hash_password("orgpass123"),
        "business_name": "Test Events Co",
        "status": "active",
        "email_verified": True,
    })
    org_data["id"] = org_id
    return org_data


@pytest.fixture
def organizer_token(organizer_user):
    return create_access_token(organizer_user["id"], role="organizer")


@pytest.fixture
def organizer_headers(organizer_token):
    return {"Authorization": f"Bearer {organizer_token}"}


# ── Category fixture ──────────────────────────────────────────────────────────

@pytest.fixture
def category():
    cat_id = str(uuid.uuid4())
    cat_data = dynamodb_helper.create_category(cat_id, {
        "name": "Technology",
        "slug": "technology",
        "icon": "💻",
        "color": "#6366f1",
        "sort_order": 1,
    })
    cat_data["id"] = cat_id
    return cat_data


# ── Event fixture ─────────────────────────────────────────────────────────────

class DictWithAttrs(dict):
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(item)


@pytest.fixture
def sample_event(organizer_user, category):
    event_id = str(uuid.uuid4())
    tt_id = str(uuid.uuid4())

    event_data = dynamodb_helper.create_event(event_id, {
        "organizer_id": organizer_user["id"],
        "category_id": category["id"],
        "title": "Test Conference 2026",
        "description": "A test conference",
        "venue_name": "Test Venue",
        "city": "Accra",
        "country": "Ghana",
        "starts_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "ends_at": (datetime.now(timezone.utc) + timedelta(days=7, hours=8)).isoformat(),
        "status": "published",
        "allow_transfers": True,
        "allow_resale": True,
        "max_resale_markup_percent": "10.00",
        "ticket_types": [
            {
                "id": tt_id,
                "name": "General Admission",
                "price": "50.00",
                "quantity": 100,
                "quantity_sold": 0,
                "purchase_limit": 5,
                "min_purchase": 1,
                "is_active": True,
            }
        ]
    })
    
    # Wrap in DictWithAttrs so both event["id"] and event.id and event.ticket_types work in tests
    wrapped = DictWithAttrs(event_data)
    wrapped["id"] = event_id
    
    tt_obj = DictWithAttrs(event_data["ticket_types"][0])
    tt_obj["id"] = tt_id
    wrapped["ticket_types"] = [tt_obj]
    return wrapped
