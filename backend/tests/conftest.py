"""Test fixtures for Ticket Hub backend."""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Set environment BEFORE importing app
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")
os.environ.setdefault("S3_BUCKET_NAME", "test-bucket")
os.environ.setdefault("SES_SENDER_EMAIL", "test@example.com")

from app.main import app
from app.db.base import Base, get_db
from app.models.models import (
    Admin, Organizer, OrganizerStatus, Event, EventStatus,
    EventCategory, TicketType,
)
from app.core.security import hash_password, create_access_token

SQLITE_URL = "sqlite:///./test.db"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


# ── Admin fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def admin_user(db):
    admin = Admin(
        email="admin@test.com",
        full_name="Test Admin",
        password_hash=hash_password("adminpass123"),
        is_super=True,
        email_verified=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def admin_token(admin_user):
    return create_access_token(admin_user.id, role="admin")


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ── Organizer fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def organizer_user(db):
    org = Organizer(
        email="org@test.com",
        full_name="Test Organizer",
        password_hash=hash_password("orgpass123"),
        business_name="Test Events Co",
        status=OrganizerStatus.active,
        email_verified=True,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def organizer_token(organizer_user):
    return create_access_token(organizer_user.id, role="organizer")


@pytest.fixture
def organizer_headers(organizer_token):
    return {"Authorization": f"Bearer {organizer_token}"}


# ── Category fixture ──────────────────────────────────────────────────────────

@pytest.fixture
def category(db):
    cat = EventCategory(name="Technology", slug="technology", icon="💻", color="#6366f1")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


# ── Event fixture ─────────────────────────────────────────────────────────────

@pytest.fixture
def sample_event(db, organizer_user, category):
    event = Event(
        organizer_id=organizer_user.id,
        category_id=category.id,
        title="Test Conference 2026",
        description="A test conference",
        venue_name="Test Venue",
        city="Accra",
        country="Ghana",
        starts_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7),
        ends_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7, hours=8),
        status=EventStatus.published,
        allow_transfers=True,
        allow_resale=True,
        max_resale_markup_percent=Decimal("10.00"),
    )
    db.add(event)
    db.flush()

    tt = TicketType(
        event_id=event.id,
        name="General Admission",
        price=Decimal("50.00"),
        quantity=100,
        purchase_limit=5,
        min_purchase=1,
    )
    db.add(tt)
    db.commit()
    db.refresh(event)
    return event


@pytest.fixture
def sample_ticket_type(db, sample_event):
    return sample_event.ticket_types[0]
