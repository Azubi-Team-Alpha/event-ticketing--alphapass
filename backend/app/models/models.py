"""
Ticket Hub – SQLAlchemy ORM Models
Full specification implementation.
"""
import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from decimal import Decimal

from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime,
    Text, Numeric, ForeignKey, UniqueConstraint, Enum as SAEnum,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, CHAR
import sqlalchemy.dialects.postgresql as pg

from app.db.base import Base


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── UUID helper (works with both SQLite and PostgreSQL) ───────────────────────

class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise stores as CHAR(36).
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(pg.UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return str(value)


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ── Enums ─────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    organizer = "organizer"


class OrganizerStatus(str, enum.Enum):
    pending   = "pending"       # awaiting email verification
    verified  = "verified"      # email verified, awaiting admin approval
    active    = "active"        # approved and active
    suspended = "suspended"     # admin suspended


class EventStatus(str, enum.Enum):
    draft     = "draft"
    pending   = "pending"       # submitted for admin approval
    published = "published"
    cancelled = "cancelled"
    archived  = "archived"


class OrderStatus(str, enum.Enum):
    pending        = "pending"
    confirmed      = "confirmed"
    cancelled      = "cancelled"
    refunded       = "refunded"
    refund_pending = "refund_pending"


class TicketStatus(str, enum.Enum):
    active      = "active"
    used        = "used"
    transferred = "transferred"
    resold      = "resold"
    cancelled   = "cancelled"


class DiscountType(str, enum.Enum):
    percentage = "percentage"
    fixed      = "fixed"


class ResaleStatus(str, enum.Enum):
    pending = "pending"
    active  = "active"
    sold    = "sold"
    removed = "removed"


class PayoutStatus(str, enum.Enum):
    pending   = "pending"
    approved  = "approved"
    processed = "processed"
    failed    = "failed"


# ── ADMIN ─────────────────────────────────────────────────────────────────────

class Admin(Base):
    __tablename__ = "admins"

    id: Any = Column(GUID, primary_key=True, default=generate_uuid) # type: ignore
    email: Any = Column(String(255), unique=True, nullable=False, index=True) # type: ignore
    full_name: Any = Column(String(255), nullable=False) # type: ignore
    password_hash: Any = Column(String(255), nullable=False) # type: ignore
    is_active: Any = Column(Boolean, default=True, nullable=False) # type: ignore
    is_super: Any = Column(Boolean, default=False, nullable=False) # type: ignore
    email_verified: Any = Column(Boolean, default=False, nullable=False) # type: ignore
    created_at: Any = Column(DateTime, default=utc_now_naive, nullable=False) # type: ignore
    updated_at: Any = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive) # type: ignore

    def __repr__(self):
        return f"<Admin {self.email}>"


# ── ORGANIZER ─────────────────────────────────────────────────────────────────

class Organizer(Base):
    __tablename__ = "organizers"

    id: Any = Column(GUID, primary_key=True, default=generate_uuid) # type: ignore
    email: Any = Column(String(255), unique=True, nullable=False, index=True) # type: ignore
    full_name: Any = Column(String(255), nullable=False) # type: ignore
    password_hash: Any = Column(String(255), nullable=False) # type: ignore
    business_name: Any = Column(String(255), nullable=True) # type: ignore
    business_description: Any = Column(Text, nullable=True) # type: ignore
    phone: Any = Column(String(50), nullable=True) # type: ignore
    website: Any = Column(String(500), nullable=True) # type: ignore
    logo_url: Any = Column(String(500), nullable=True) # type: ignore
    status: Any = Column(SAEnum(OrganizerStatus), default=OrganizerStatus.pending, nullable=False) # type: ignore
    email_verified: Any = Column(Boolean, default=False, nullable=False) # type: ignore
    verification_token: Any = Column(String(255), nullable=True) # type: ignore
    reset_token: Any = Column(String(255), nullable=True) # type: ignore
    reset_token_expires: Any = Column(DateTime, nullable=True) # type: ignore
    commission_rate: Any = Column(Numeric(5, 2), nullable=True) # type: ignore
    created_at: Any = Column(DateTime, default=utc_now_naive, nullable=False) # type: ignore
    updated_at: Any = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive) # type: ignore

    events      = relationship("Event", back_populates="organizer", cascade="all, delete")
    promo_codes = relationship("PromoCode", back_populates="organizer")
    payouts     = relationship("OrganizerPayout", back_populates="organizer")

    def __repr__(self):
        return f"<Organizer {self.email}>"


# ── EVENT CATEGORY ────────────────────────────────────────────────────────────

class EventCategory(Base):
    __tablename__ = "event_categories"

    id: Any = Column(GUID, primary_key=True, default=generate_uuid) # type: ignore
    name: Any = Column(String(100), unique=True, nullable=False) # type: ignore
    slug: Any = Column(String(100), unique=True, nullable=False) # type: ignore
    icon: Any = Column(String(100), nullable=True) # type: ignore
    color: Any = Column(String(50), nullable=True) # type: ignore

    events = relationship("Event", back_populates="category")

    def __repr__(self):
        return f"<EventCategory {self.name}>"


# ── EVENT ─────────────────────────────────────────────────────────────────────

class Event(Base):
    __tablename__ = "events"

    id: Any = Column(GUID, primary_key=True, default=generate_uuid) # type: ignore
    organizer_id: Any = Column(GUID, ForeignKey("organizers.id", ondelete="CASCADE"), nullable=False) # type: ignore
    category_id: Any = Column(GUID, ForeignKey("event_categories.id"), nullable=True) # type: ignore

    title: Any = Column(String(255), nullable=False) # type: ignore
    description: Any = Column(Text, nullable=True) # type: ignore
    policies: Any = Column(Text, nullable=True) # type: ignore
    banner_image_url: Any = Column(String(500), nullable=True) # type: ignore
    thumbnail_url: Any = Column(String(500), nullable=True) # type: ignore

    # Location
    venue_name: Any = Column(String(255), nullable=True) # type: ignore
    address: Any = Column(String(500), nullable=True) # type: ignore
    city: Any = Column(String(100), nullable=True) # type: ignore
    country: Any = Column(String(100), nullable=True) # type: ignore
    is_online: Any = Column(Boolean, default=False, nullable=False) # type: ignore
    online_url: Any = Column(String(500), nullable=True) # type: ignore

    starts_at: Any = Column(DateTime, nullable=False) # type: ignore
    ends_at: Any = Column(DateTime, nullable=False) # type: ignore

    status: Any = Column(SAEnum(EventStatus), default=EventStatus.draft, nullable=False) # type: ignore
    is_featured: Any = Column(Boolean, default=False, nullable=False) # type: ignore

    # Transfer / resale settings
    allow_transfers: Any = Column(Boolean, default=True, nullable=False) # type: ignore
    transfer_deadline_hours: Any = Column(Integer, default=24) # type: ignore
    max_transfers_per_ticket: Any = Column(Integer, default=1) # type: ignore
    allow_resale: Any = Column(Boolean, default=False, nullable=False) # type: ignore
    max_resale_markup_percent: Any = Column(Numeric(5, 2), default=10.00) # type: ignore
    group_discount_threshold: Any = Column(Integer, nullable=True) # type: ignore
    group_discount_percent: Any = Column(Numeric(5, 2), nullable=True) # type: ignore
    allow_refunds: Any = Column(Boolean, default=True, nullable=False) # type: ignore

    # Admin approval
    approved_by: Any = Column(GUID, ForeignKey("admins.id"), nullable=True) # type: ignore
    approved_at: Any = Column(DateTime, nullable=True) # type: ignore
    rejection_reason: Any = Column(Text, nullable=True) # type: ignore

    created_at: Any = Column(DateTime, default=utc_now_naive, nullable=False) # type: ignore
    updated_at: Any = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive) # type: ignore

    organizer    = relationship("Organizer", back_populates="events")
    category     = relationship("EventCategory", back_populates="events")
    ticket_types = relationship("TicketType", back_populates="event", cascade="all, delete")
    orders       = relationship("Order", back_populates="event")
    promo_codes  = relationship("PromoCode", back_populates="event")

    @property
    def total_capacity(self) -> int:
        return sum(tt.quantity for tt in self.ticket_types)

    @property
    def total_sold(self) -> int:
        return sum(tt.quantity_sold for tt in self.ticket_types)

    def __repr__(self):
        return f"<Event {self.title}>"


# ── TICKET TYPE ───────────────────────────────────────────────────────────────

class TicketType(Base):
    __tablename__ = "ticket_types"

    id: Any = Column(GUID, primary_key=True, default=generate_uuid) # type: ignore
    event_id: Any = Column(GUID, ForeignKey("events.id", ondelete="CASCADE"), nullable=False) # type: ignore

    name: Any = Column(String(100), nullable=False) # type: ignore
    description: Any = Column(Text, nullable=True) # type: ignore
    benefits: Any = Column(JSON, nullable=True) # type: ignore
    price: Any = Column(Numeric(10, 2), default=0.00, nullable=False) # type: ignore
    quantity: Any = Column(Integer, nullable=False) # type: ignore
    quantity_sold: Any = Column(Integer, default=0, nullable=False) # type: ignore

    sales_start: Any = Column(DateTime, nullable=True) # type: ignore
    sales_end: Any = Column(DateTime, nullable=True) # type: ignore
    purchase_limit: Any = Column(Integer, default=10, nullable=False) # type: ignore
    min_purchase: Any = Column(Integer, default=1, nullable=False) # type: ignore

    is_active: Any = Column(Boolean, default=True, nullable=False) # type: ignore
    sort_order: Any = Column(Integer, default=0, nullable=False) # type: ignore

    created_at: Any = Column(DateTime, default=utc_now_naive, nullable=False) # type: ignore
    updated_at: Any = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive) # type: ignore

    event       = relationship("Event", back_populates="ticket_types")
    order_items = relationship("OrderItem", back_populates="ticket_type")

    @property
    def quantity_remaining(self) -> int:
        return max(0, self.quantity - self.quantity_sold)  # type: ignore

    @property
    def is_sold_out(self) -> bool:
        return self.quantity_remaining == 0

    def __repr__(self):
        return f"<TicketType {self.name} @ {self.event_id}>"


# ── PROMO CODE ────────────────────────────────────────────────────────────────

class PromoCode(Base):
    __tablename__ = "promo_codes"

    id: Any = Column(GUID, primary_key=True, default=generate_uuid) # type: ignore
    event_id: Any = Column(GUID, ForeignKey("events.id", ondelete="CASCADE"), nullable=False) # type: ignore
    organizer_id: Any = Column(GUID, ForeignKey("organizers.id"), nullable=False) # type: ignore

    code: Any = Column(String(50), nullable=False) # type: ignore
    discount_type: Any = Column(SAEnum(DiscountType), nullable=False) # type: ignore
    discount_value: Any = Column(Numeric(10, 2), nullable=False) # type: ignore
    max_uses: Any = Column(Integer, nullable=True) # type: ignore
    used_count: Any = Column(Integer, default=0, nullable=False) # type: ignore
    applicable_ticket_type_ids: Any = Column(JSON, nullable=True) # type: ignore
    expires_at: Any = Column(DateTime, nullable=True) # type: ignore
    is_active: Any = Column(Boolean, default=True, nullable=False) # type: ignore
    created_at: Any = Column(DateTime, default=utc_now_naive, nullable=False) # type: ignore

    __table_args__ = (
        UniqueConstraint("event_id", "code", name="uq_event_promo_code"),
    )

    event     = relationship("Event", back_populates="promo_codes")
    organizer = relationship("Organizer", back_populates="promo_codes")
    orders    = relationship("Order", back_populates="promo_code")

    def __repr__(self):
        return f"<PromoCode {self.code}>"


# ── ORDER ─────────────────────────────────────────────────────────────────────

class Order(Base):
    __tablename__ = "orders"

    id: Any = Column(GUID, primary_key=True, default=generate_uuid) # type: ignore
    event_id: Any = Column(GUID, ForeignKey("events.id"), nullable=False) # type: ignore
    promo_code_id: Any = Column(GUID, ForeignKey("promo_codes.id"), nullable=True) # type: ignore

    guest_name: Any = Column(String(255), nullable=False) # type: ignore
    guest_email: Any = Column(String(255), nullable=False, index=True) # type: ignore
    guest_phone: Any = Column(String(50), nullable=True) # type: ignore

    status: Any = Column(SAEnum(OrderStatus), default=OrderStatus.pending, nullable=False) # type: ignore
    subtotal: Any = Column(Numeric(10, 2), default=0.00, nullable=False) # type: ignore
    discount_amount: Any = Column(Numeric(10, 2), default=0.00, nullable=False) # type: ignore
    platform_fee: Any = Column(Numeric(10, 2), default=0.00, nullable=False) # type: ignore
    total_amount: Any = Column(Numeric(10, 2), default=0.00, nullable=False) # type: ignore

    payment_reference: Any = Column(String(255), nullable=True) # type: ignore
    payment_method: Any = Column(String(100), nullable=True) # type: ignore

    created_at: Any = Column(DateTime, default=utc_now_naive, nullable=False) # type: ignore
    updated_at: Any = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive) # type: ignore

    event      = relationship("Event", back_populates="orders")
    promo_code = relationship("PromoCode", back_populates="orders")
    items      = relationship("OrderItem", back_populates="order", cascade="all, delete")

    @property
    def total_tickets(self) -> int:
        return sum(item.quantity for item in self.items)

    def __repr__(self):
        return f"<Order {self.id} by {self.guest_email}>"


# ── ORDER ITEM ────────────────────────────────────────────────────────────────

class OrderItem(Base):
    __tablename__ = "order_items"

    id: Any = Column(GUID, primary_key=True, default=generate_uuid) # type: ignore
    order_id: Any = Column(GUID, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False) # type: ignore
    ticket_type_id: Any = Column(GUID, ForeignKey("ticket_types.id"), nullable=False) # type: ignore

    quantity: Any = Column(Integer, nullable=False, default=1) # type: ignore
    unit_price: Any = Column(Numeric(10, 2), nullable=False) # type: ignore
    line_total: Any = Column(Numeric(10, 2), nullable=False) # type: ignore

    created_at: Any = Column(DateTime, default=utc_now_naive, nullable=False) # type: ignore

    order       = relationship("Order", back_populates="items")
    ticket_type = relationship("TicketType", back_populates="order_items")
    tickets     = relationship("Ticket", back_populates="order_item", cascade="all, delete")

    def __repr__(self):
        return f"<OrderItem {self.quantity}x {self.ticket_type_id}>"


# ── TICKET ────────────────────────────────────────────────────────────────────

class Ticket(Base):
    __tablename__ = "tickets"

    id: Any = Column(GUID, primary_key=True, default=generate_uuid) # type: ignore
    order_item_id: Any = Column(GUID, ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False) # type: ignore

    ticket_code: Any = Column(String(100), unique=True, nullable=False, default=generate_uuid) # type: ignore
    qr_image_url: Any = Column(String(500), nullable=True) # type: ignore

    attendee_name: Any = Column(String(255), nullable=True) # type: ignore
    attendee_email: Any = Column(String(255), nullable=True) # type: ignore

    status: Any = Column(SAEnum(TicketStatus), default=TicketStatus.active, nullable=False) # type: ignore
    is_used: Any = Column(Boolean, default=False, nullable=False) # type: ignore
    used_at: Any = Column(DateTime, nullable=True) # type: ignore
    issued_at: Any = Column(DateTime, default=utc_now_naive, nullable=False) # type: ignore

    order_item      = relationship("OrderItem", back_populates="tickets")
    transfers       = relationship("TicketTransfer", back_populates="ticket", cascade="all, delete")
    resale_listings = relationship(
        "ResaleListing", back_populates="ticket",
        foreign_keys="[ResaleListing.ticket_id]",
    )

    @property
    def event(self):
        try:
            return self.order_item.order.event
        except Exception:
            return None

    @property
    def ticket_type(self):
        try:
            return self.order_item.ticket_type
        except Exception:
            return None

    def __repr__(self):
        return f"<Ticket {self.ticket_code}>"


# ── TICKET TRANSFER ───────────────────────────────────────────────────────────

class TicketTransfer(Base):
    __tablename__ = "ticket_transfers"

    id: Any = Column(GUID, primary_key=True, default=generate_uuid) # type: ignore
    ticket_id: Any = Column(GUID, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False) # type: ignore

    from_name: Any = Column(String(255), nullable=False) # type: ignore
    from_email: Any = Column(String(255), nullable=False) # type: ignore
    to_name: Any = Column(String(255), nullable=False) # type: ignore
    to_email: Any = Column(String(255), nullable=False) # type: ignore

    is_completed: Any = Column(Boolean, default=False, nullable=False) # type: ignore
    transferred_at: Any = Column(DateTime, nullable=True) # type: ignore
    created_at: Any = Column(DateTime, default=utc_now_naive, nullable=False) # type: ignore

    ticket = relationship("Ticket", back_populates="transfers")

    def __repr__(self):
        return f"<TicketTransfer {self.ticket_id} -> {self.to_email}>"


# ── RESALE LISTING ────────────────────────────────────────────────────────────

class ResaleListing(Base):
    __tablename__ = "resale_listings"

    id: Any = Column(GUID, primary_key=True, default=generate_uuid) # type: ignore
    ticket_id: Any = Column(GUID, ForeignKey("tickets.id"), nullable=False) # type: ignore

    seller_name: Any = Column(String(255), nullable=False) # type: ignore
    seller_email: Any = Column(String(255), nullable=False) # type: ignore
    asking_price: Any = Column(Numeric(10, 2), nullable=False) # type: ignore
    face_value: Any = Column(Numeric(10, 2), nullable=False) # type: ignore

    status: Any = Column(SAEnum(ResaleStatus), default=ResaleStatus.active, nullable=False) # type: ignore
    listed_at: Any = Column(DateTime, default=utc_now_naive, nullable=False) # type: ignore
    sold_at: Any = Column(DateTime, nullable=True) # type: ignore

    buyer_name: Any = Column(String(255), nullable=True) # type: ignore
    buyer_email: Any = Column(String(255), nullable=True) # type: ignore
    buyer_ticket_id: Any = Column(GUID, ForeignKey("tickets.id"), nullable=True) # type: ignore

    ticket       = relationship("Ticket", back_populates="resale_listings",
                                foreign_keys=[ticket_id])
    buyer_ticket = relationship("Ticket", foreign_keys=[buyer_ticket_id])

    def __repr__(self):
        return f"<ResaleListing {self.ticket_id} @ {self.asking_price}>"


# ── ORGANIZER PAYOUT ──────────────────────────────────────────────────────────

class OrganizerPayout(Base):
    __tablename__ = "organizer_payouts"

    id: Any = Column(GUID, primary_key=True, default=generate_uuid) # type: ignore
    organizer_id: Any = Column(GUID, ForeignKey("organizers.id"), nullable=False) # type: ignore

    amount: Any = Column(Numeric(10, 2), nullable=False) # type: ignore
    currency: Any = Column(String(10), default="GHS", nullable=False) # type: ignore
    status: Any = Column(SAEnum(PayoutStatus), default=PayoutStatus.pending, nullable=False) # type: ignore
    period_start: Any = Column(DateTime, nullable=True) # type: ignore
    period_end: Any = Column(DateTime, nullable=True) # type: ignore
    processed_at: Any = Column(DateTime, nullable=True) # type: ignore
    notes: Any = Column(Text, nullable=True) # type: ignore
    created_at: Any = Column(DateTime, default=utc_now_naive, nullable=False) # type: ignore

    organizer = relationship("Organizer", back_populates="payouts")

    def __repr__(self):
        return f"<OrganizerPayout {self.organizer_id} {self.amount}>"


# ── PLATFORM SETTINGS ─────────────────────────────────────────────────────────

class PlatformSettings(Base):
    __tablename__ = "platform_settings"

    id: Any = Column(GUID, primary_key=True, default=generate_uuid) # type: ignore
    key: Any = Column(String(100), unique=True, nullable=False) # type: ignore
    value: Any = Column(Text, nullable=True) # type: ignore
    description: Any = Column(String(500), nullable=True) # type: ignore
    updated_at: Any = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive) # type: ignore

    def __repr__(self):
        return f"<PlatformSettings {self.key}={self.value}>"


# ── AUDIT LOG ─────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Any = Column(GUID, primary_key=True, default=generate_uuid) # type: ignore
    actor_type: Any = Column(String(50), nullable=False) # type: ignore
    actor_id: Any = Column(String(255), nullable=True) # type: ignore
    actor_email: Any = Column(String(255), nullable=True) # type: ignore
    action: Any = Column(String(100), nullable=False) # type: ignore
    resource_type: Any = Column(String(100), nullable=True) # type: ignore
    resource_id: Any = Column(String(255), nullable=True) # type: ignore
    meta: Any = Column(JSON, nullable=True) # type: ignore
    ip_address: Any = Column(String(50), nullable=True) # type: ignore
    created_at: Any = Column(DateTime, default=utc_now_naive, nullable=False) # type: ignore

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.actor_email}>"
