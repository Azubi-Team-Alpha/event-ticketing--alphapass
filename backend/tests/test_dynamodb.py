import os
import pytest
import boto3
from moto import mock_aws
from decimal import Decimal
from app.db.dynamodb import DynamoDBHelper

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["ENV"] = "test"

@pytest.fixture
def mock_db(aws_credentials):
    with mock_aws():
        db = boto3.resource("dynamodb", region_name="us-east-1")
        
        # Create all 12 DynamoDB tables mock
        tables = [
            ("alphapass-events-test", "EventID"),
            ("alphapass-registrations-test", "RegistrationID"),
            ("alphapass-organizers-test", "OrganizerID"),
            ("alphapass-admins-test", "AdminID"),
            ("alphapass-orders-test", "OrderID"),
            ("alphapass-tickets-test", "TicketID"),
            ("alphapass-promo-codes-test", "Code"),
            ("alphapass-resale-listings-test", "ListingID"),
            ("alphapass-transfers-test", "TransferID"),
            ("alphapass-payouts-test", "PayoutID"),
            ("alphapass-platform-settings-test", "SettingKey"),
            ("alphapass-audit-logs-test", "LogID"),
            ("alphapass-event-categories-test", "CategoryID")
        ]
        
        for name, key in tables:
            db.create_table(
                TableName=name,
                KeySchema=[{"AttributeName": key, "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": key, "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST"
            )
            
        yield DynamoDBHelper()

def test_events_operations(mock_db):
    event_id = "test-event-123"
    event_data = {
        "title": "Alpha Summit 2026",
        "description": "Serverless event",
        "price": 49.99,
        "is_online": True
    }
    
    created = mock_db.create_event(event_id, event_data)
    assert created["EventID"] == event_id
    assert created["price"] == 49.99
    
    retrieved = mock_db.get_event(event_id)
    assert retrieved is not None
    assert retrieved["price"] == 49.99
    
    updated = mock_db.update_event(event_id, {"title": "Updated Summit", "price": 59.99})
    assert updated["title"] == "Updated Summit"
    assert updated["price"] == 59.99

def test_organizers_and_admins(mock_db):
    org_id = "org-111"
    org_data = {"full_name": "Event Master", "email": "master@events.com"}
    org = mock_db.create_organizer(org_id, org_data)
    assert org["OrganizerID"] == org_id
    assert mock_db.get_organizer(org_id)["email"] == "master@events.com"
    
    admin_id = "admin-222"
    admin_data = {"full_name": "Super Admin", "email": "admin@platform.com"}
    admin = mock_db.create_admin(admin_id, admin_data)
    assert admin["AdminID"] == admin_id
    assert mock_db.get_admin(admin_id)["email"] == "admin@platform.com"

def test_orders_and_tickets(mock_db):
    order_id = "order-555"
    order_data = {"total": 150.00, "status": "pending"}
    order = mock_db.create_order(order_id, order_data)
    assert order["OrderID"] == order_id
    assert mock_db.get_order(order_id)["total"] == 150.0
    
    ticket_id = "tkt-777"
    ticket_data = {"ticket_code": "TC-XYZ", "price": 50.00, "is_used": False}
    ticket = mock_db.create_ticket(ticket_id, ticket_data)
    assert ticket["TicketID"] == ticket_id
    assert mock_db.get_ticket(ticket_id)["ticket_code"] == "TC-XYZ"
    
    updated_tkt = mock_db.update_ticket(ticket_id, {"is_used": True})
    assert updated_tkt["is_used"] is True

def test_promo_codes_and_resale(mock_db):
    code = "SUMMER20"
    promo_data = {"discount_percent": 20.0, "active": True}
    promo = mock_db.create_promo_code(code, promo_data)
    assert promo["Code"] == code
    assert mock_db.get_promo_code(code)["discount_percent"] == 20.0
    
    listing_id = "list-888"
    resale_data = {"ticket_id": "tkt-123", "price": 40.00, "status": "active"}
    listing = mock_db.create_resale_listing(listing_id, resale_data)
    assert listing["ListingID"] == listing_id
    assert mock_db.get_resale_listing(listing_id)["price"] == 40.0

def test_settings_and_categories(mock_db):
    mock_db.set_platform_setting("commission", 5.5)
    setting = mock_db.get_platform_setting("commission")
    assert setting["value"] == 5.5
    
    cat_id = "cat-tech"
    cat_data = {"name": "Technology", "slug": "tech"}
    cat = mock_db.create_category(cat_id, cat_data)
    assert cat["CategoryID"] == cat_id
    assert mock_db.get_category(cat_id)["name"] == "Technology"
