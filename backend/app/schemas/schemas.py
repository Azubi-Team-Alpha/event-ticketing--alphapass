"""
Ticket Hub – Pydantic schemas, organized by domain.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Literal, Optional
from pydantic import BaseModel, EmailStr, field_validator, model_validator


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════════════════════════════════════

class HealthResponse(BaseModel):
    status: str
    db: str
    timestamp: datetime


# ══════════════════════════════════════════════════════════════════════════════
# AUTH – ADMIN
# ══════════════════════════════════════════════════════════════════════════════

class AdminRegister(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    invite_code: Optional[str] = None   # optional initial invite gate

    @field_validator("password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class AdminResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    is_super: bool
    email_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# AUTH – ORGANIZER
# ══════════════════════════════════════════════════════════════════════════════

class OrganizerRegister(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    business_name: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class OrganizerLogin(BaseModel):
    email: EmailStr
    password: str


class OrganizerResponse(BaseModel):
    id: str
    email: str
    full_name: str
    business_name: Optional[str] = None
    business_description: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    status: str
    email_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizerProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    business_name: Optional[str] = None
    business_description: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class EmailVerification(BaseModel):
    token: str


# ══════════════════════════════════════════════════════════════════════════════
# EVENT CATEGORY
# ══════════════════════════════════════════════════════════════════════════════

class EventCategoryCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class EventCategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    icon: Optional[str] = None
    color: Optional[str] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# TICKET TYPE
# ══════════════════════════════════════════════════════════════════════════════

class TicketTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    benefits: Optional[list[str]] = None
    price: Decimal = Decimal("0.00")
    quantity: int
    sales_start: Optional[datetime] = None
    sales_end: Optional[datetime] = None
    purchase_limit: int = 10
    min_purchase: int = 1
    sort_order: int = 0

    @field_validator("quantity")
    def quantity_positive(cls, v):
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v

    @field_validator("price")
    def price_non_negative(cls, v):
        if v < 0:
            raise ValueError("Price cannot be negative")
        return v


class TicketTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    benefits: Optional[list[str]] = None
    price: Optional[Decimal] = None
    quantity: Optional[int] = None
    sales_start: Optional[datetime] = None
    sales_end: Optional[datetime] = None
    purchase_limit: Optional[int] = None
    min_purchase: Optional[int] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class TicketTypeResponse(BaseModel):
    id: str
    event_id: str
    name: str
    description: Optional[str] = None
    benefits: Optional[list[str]] = None
    price: Decimal
    quantity: int
    quantity_sold: int
    quantity_remaining: int
    sales_start: Optional[datetime] = None
    sales_end: Optional[datetime] = None
    purchase_limit: int = 10
    min_purchase: int = 1
    is_active: bool = True
    is_sold_out: bool = False
    sort_order: int = 0

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# EVENT
# ══════════════════════════════════════════════════════════════════════════════

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    policies: Optional[str] = None
    category_id: Optional[str] = None

    # Image / Banner
    banner_image_url: Optional[str] = None
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    # Location
    venue_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    is_online: bool = False
    online_url: Optional[str] = None

    starts_at: datetime
    ends_at: datetime

    # Transfer / resale settings
    allow_transfers: bool = True
    transfer_deadline_hours: int = 24
    max_transfers_per_ticket: int = 1
    allow_resale: bool = False
    max_resale_markup_percent: Decimal = Decimal("10.00")
    group_discount_threshold: Optional[int] = None
    group_discount_percent: Optional[Decimal] = None
    allow_refunds: bool = True

    @field_validator("ends_at")
    def ends_after_starts(cls, v, info):
        if "starts_at" in info.data and v <= info.data["starts_at"]:
            return info.data["starts_at"] + timedelta(hours=4)
        return v


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    policies: Optional[str] = None
    category_id: Optional[str] = None
    banner_image_url: Optional[str] = None
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    venue_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    is_online: Optional[bool] = None
    online_url: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    allow_transfers: Optional[bool] = None
    transfer_deadline_hours: Optional[int] = None
    max_transfers_per_ticket: Optional[int] = None
    allow_resale: Optional[bool] = None
    max_resale_markup_percent: Optional[Decimal] = None
    group_discount_threshold: Optional[int] = None
    group_discount_percent: Optional[Decimal] = None
    allow_refunds: Optional[bool] = None
    is_published: Optional[bool] = None



class EventResponse(BaseModel):
    id: str
    organizer_id: str
    category: Optional[EventCategoryResponse] = None
    title: str
    description: Optional[str]
    policies: Optional[str]
    banner_image_url: Optional[str]
    thumbnail_url: Optional[str]
    venue_name: Optional[str]
    address: Optional[str]
    city: Optional[str]
    country: Optional[str]
    is_online: bool
    online_url: Optional[str]
    starts_at: datetime
    ends_at: datetime
    status: str
    is_featured: bool
    allow_transfers: bool
    allow_resale: bool
    group_discount_threshold: Optional[int]
    group_discount_percent: Optional[Decimal]
    allow_refunds: bool
    ticket_types: list[TicketTypeResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class EventListItem(BaseModel):
    """Lighter event object for list views."""
    id: str
    title: str
    banner_image_url: Optional[str]
    thumbnail_url: Optional[str]
    venue_name: Optional[str]
    city: Optional[str]
    country: Optional[str]
    is_online: bool
    starts_at: datetime
    ends_at: datetime
    status: str
    is_featured: bool
    category: Optional[EventCategoryResponse] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    total_capacity: Optional[int] = None
    total_sold: Optional[int] = None

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    items: list[EventListItem]
    total: int
    page: int
    limit: int


# ══════════════════════════════════════════════════════════════════════════════
# PROMO CODE
# ══════════════════════════════════════════════════════════════════════════════

class PromoCodeCreate(BaseModel):
    code: str
    discount_type: str          # "percentage" | "fixed"
    discount_value: Decimal
    max_uses: Optional[int] = None
    applicable_ticket_type_ids: Optional[list[str]] = None
    expires_at: Optional[datetime] = None

    @field_validator("discount_value")
    def discount_positive(cls, v):
        if v <= 0:
            raise ValueError("Discount value must be positive")
        return v


class PromoCodeResponse(BaseModel):
    id: str
    event_id: str
    code: str
    discount_type: str
    discount_value: Decimal
    max_uses: Optional[int]
    used_count: int
    expires_at: Optional[datetime]
    is_active: bool

    model_config = {"from_attributes": True}


class ApplyPromoCode(BaseModel):
    code: str
    event_id: str


class PromoCodeValidation(BaseModel):
    valid: bool
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = None
    message: str


# ══════════════════════════════════════════════════════════════════════════════
# ORDER (Guest Checkout)
# ══════════════════════════════════════════════════════════════════════════════

class OrderItemCreate(BaseModel):
    ticket_type_id: str
    quantity: int
    attendee_name: Optional[str] = None     # for bulk, set per ticket later
    attendee_email: Optional[str] = None

    @field_validator("quantity")
    def quantity_positive(cls, v):
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v


class OrderCreate(BaseModel):
    event_id: str
    guest_name: str
    guest_email: EmailStr
    guest_phone: Optional[str] = None
    items: list[OrderItemCreate]
    promo_code: Optional[str] = None
    payment_reference: Optional[str] = None
    payment_method: Optional[str] = None

    @field_validator("items")
    def items_not_empty(cls, v):
        if not v:
            raise ValueError("Order must have at least one item")
        return v


class TicketInOrder(BaseModel):
    id: str
    ticket_code: str
    qr_image_url: Optional[str]
    attendee_name: Optional[str]
    attendee_email: Optional[str]
    status: str

    model_config = {"from_attributes": True}


class OrderItemResponse(BaseModel):
    id: str
    ticket_type_id: str
    ticket_type_name: Optional[str] = None
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    tickets: list[TicketInOrder] = []

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: str
    event_id: str
    guest_name: str
    guest_email: str
    guest_phone: Optional[str] = None
    status: str
    subtotal: Decimal
    discount_amount: Decimal
    platform_fee: Decimal
    total_amount: Decimal
    payment_reference: Optional[str] = None
    items: list[OrderItemResponse] = []
    tickets: list[TicketResponse] = []
    total_tickets: int
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderLookup(BaseModel):
    order_id: Optional[str] = None
    guest_email: Optional[EmailStr] = None
    email: Optional[EmailStr] = None


# ══════════════════════════════════════════════════════════════════════════════
# TICKET
# ══════════════════════════════════════════════════════════════════════════════

class TicketResponse(BaseModel):
    id: str
    ticket_code: str
    qr_image_url: Optional[str]
    attendee_name: Optional[str]
    attendee_email: Optional[str]
    status: str
    is_used: bool
    used_at: Optional[datetime]
    issued_at: datetime

    model_config = {"from_attributes": True}


class AttendeeUpdate(BaseModel):
    attendee_name: str
    attendee_email: Optional[EmailStr] = None


class ValidateTicketResponse(BaseModel):
    valid: bool
    message: str
    ticket: TicketResponse


# ══════════════════════════════════════════════════════════════════════════════
# TRANSFER
# ══════════════════════════════════════════════════════════════════════════════

class TransferRequest(BaseModel):
    to_name: str
    to_email: EmailStr


class TransferResponse(BaseModel):
    id: str
    ticket_id: str
    from_name: str
    from_email: str
    to_name: str
    to_email: str
    is_completed: bool
    transferred_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# RESALE
# ══════════════════════════════════════════════════════════════════════════════

class ResaleListingCreate(BaseModel):
    seller_name: str
    seller_email: EmailStr
    asking_price: Decimal

    @field_validator("asking_price")
    def price_positive(cls, v):
        if v <= 0:
            raise ValueError("Asking price must be positive")
        return v


class ResaleListingResponse(BaseModel):
    id: str
    ticket_id: str
    ticket_code: Optional[str] = None
    event_title: Optional[str] = None
    seller_name: str
    seller_email: Optional[str] = None
    asking_price: Decimal
    face_value: Decimal
    status: str
    listed_at: datetime
    sold_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ResalePurchase(BaseModel):
    buyer_name: str
    buyer_email: EmailStr


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN – PLATFORM
# ══════════════════════════════════════════════════════════════════════════════

class PlatformStats(BaseModel):
    total_organizers: int
    active_organizers: int
    total_events: int
    published_events: int
    total_orders: int
    total_tickets_sold: int
    total_revenue: Decimal
    total_platform_fees: Decimal
    total_refunds: int


class CommissionUpdate(BaseModel):
    commission_percent: float = 5.0

    @model_validator(mode="before")
    @classmethod
    def extract_commission(cls, data: Any) -> Any:
        if isinstance(data, dict):
            val = data.get("commission_percent") if data.get("commission_percent") is not None else (data.get("commission_rate") if data.get("commission_rate") is not None else data.get("rate"))
            if val is not None:
                return {**data, "commission_percent": float(val)}
        return data

    @field_validator("commission_percent")
    def commission_valid(cls, v):
        if not (0 <= v <= 100):
            raise ValueError("Commission must be between 0 and 100")
        return v


class OrganizerAdminResponse(BaseModel):
    id: str
    email: str
    full_name: str
    business_name: Optional[str]
    status: str
    email_verified: bool
    total_events: int = 0
    total_revenue: Decimal = Decimal("0.00")
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizerStatusUpdate(BaseModel):
    status: Literal["active", "suspended", "verified"]
    reason: Optional[str] = None


class EventApproval(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = None


class PayoutRequest(BaseModel):
    organizer_id: str
    amount: Decimal
    notes: Optional[str] = None


class PayoutResponse(BaseModel):
    id: str
    organizer_id: str
    amount: Decimal
    currency: str = "GHS"
    status: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# ORGANIZER DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

class OrganizerDashboard(BaseModel):
    total_events: int
    published_events: int
    total_orders: int
    total_tickets_sold: int
    gross_revenue: Decimal
    platform_fees: Decimal
    net_earnings: Decimal
    pending_payout: Decimal
    total_transfers: int
    total_resale_listings: int


class EventAnalytics(BaseModel):
    event_id: str
    event_title: str
    total_capacity: int
    total_sold: int
    attendance_rate: float
    gross_revenue: Decimal
    refund_count: int
    transfer_count: int
    resale_count: int
    ticket_type_breakdown: list[dict[str, Any]]


# ══════════════════════════════════════════════════════════════════════════════
# CHECKIN
# ══════════════════════════════════════════════════════════════════════════════

class CheckInRequest(BaseModel):
    ticket_code: str


class CheckInResponse(BaseModel):
    valid: bool
    message: str
    ticket: Optional[TicketResponse] = None
    attendee_name: Optional[str] = None
    ticket_type_name: Optional[str] = None
    event_title: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG
# ══════════════════════════════════════════════════════════════════════════════

class AuditLogResponse(BaseModel):
    id: str
    actor_type: str
    actor_email: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# ADDITIONAL SCHEMAS FOR SPEC COMPLIANCE
# ══════════════════════════════════════════════════════════════════════════════

class RefundRequest(BaseModel):
    guest_email: EmailStr
    reason: Optional[str] = None


class RefundApproval(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = None


class ResaleApproval(BaseModel):
    approved: bool


class AdminCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    is_super: bool = False
