"""Platform Administrator routes."""
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.base import get_db
from app.models.models import (
    Admin, Organizer, OrganizerStatus, Event, EventStatus,
    Order, OrderStatus, Ticket, AuditLog, OrganizerPayout, PayoutStatus,
    EventCategory, PlatformSettings, OrderItem, TicketStatus, ResaleListing, ResaleStatus,
)
from app.schemas.schemas import (
    PlatformStats, OrganizerAdminResponse, OrganizerStatusUpdate,
    EventApproval, AdminResponse, PayoutRequest, PayoutResponse,
    EventCategoryCreate, EventCategoryResponse, CommissionUpdate, AuditLogResponse,
    AdminCreate, RefundApproval, ResaleApproval,
)
from app.core.dependencies import get_current_admin, get_super_admin

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=PlatformStats)
def platform_dashboard(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    total_organizers = db.query(Organizer).count()
    active_organizers = db.query(Organizer).filter(Organizer.status == OrganizerStatus.active).count()
    total_events = db.query(Event).count()
    published_events = db.query(Event).filter(Event.status == EventStatus.published).count()
    total_orders = db.query(Order).filter(Order.status == OrderStatus.confirmed).count()
    total_refunds = db.query(Order).filter(Order.status == OrderStatus.refunded).count()

    revenue_row = db.query(func.sum(Order.total_amount)).filter(Order.status == OrderStatus.confirmed).scalar()
    fees_row = db.query(func.sum(Order.platform_fee)).filter(Order.status == OrderStatus.confirmed).scalar()
    total_revenue = Decimal(str(revenue_row)) if revenue_row else Decimal("0.00")
    platform_fees = Decimal(str(fees_row)) if fees_row else Decimal("0.00")

    tickets_sold = db.query(func.sum(OrderItem.quantity)).join(Order).filter(Order.status == OrderStatus.confirmed).scalar() or 0

    return PlatformStats(
        total_organizers=total_organizers,
        active_organizers=active_organizers,
        total_events=total_events,
        published_events=published_events,
        total_orders=total_orders,
        total_tickets_sold=tickets_sold,
        total_revenue=total_revenue,
        total_platform_fees=platform_fees,
        total_refunds=total_refunds,
    )


# ── Organizer Management ──────────────────────────────────────────────────────

@router.get("/organizers", response_model=list[OrganizerAdminResponse])
def list_organizers(
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    query = db.query(Organizer)
    if status:
        query = query.filter(Organizer.status == OrganizerStatus(status))
    orgs = query.offset((page - 1) * limit).limit(limit).all()
    result = []
    for org in orgs:
        total_events = db.query(Event).filter(Event.organizer_id == org.id).count()
        rev = db.query(func.sum(Order.total_amount)).filter(
            Order.event_id.in_(
                db.query(Event.id).filter(Event.organizer_id == org.id).scalar_subquery()
            ),
            Order.status == OrderStatus.confirmed,
        ).scalar()
        result.append({
            "id": org.id, "email": org.email, "full_name": org.full_name,
            "business_name": org.business_name, "status": org.status.value,
            "email_verified": org.email_verified, "total_events": total_events,
            "total_revenue": Decimal(str(rev)) if rev else Decimal("0.00"),
            "created_at": org.created_at,
        })
    return result


@router.get("/organizers/{organizer_id}", response_model=OrganizerAdminResponse)
def get_organizer(
    organizer_id: str, db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    org = db.query(Organizer).filter(Organizer.id == organizer_id).first()
    if not org:
        raise HTTPException(404, "Organizer not found")
    total_events = db.query(Event).filter(Event.organizer_id == org.id).count()
    return {
        "id": org.id, "email": org.email, "full_name": org.full_name,
        "business_name": org.business_name, "status": org.status.value,
        "email_verified": org.email_verified, "total_events": total_events,
        "total_revenue": Decimal("0.00"), "created_at": org.created_at,
    }


@router.put("/organizers/{organizer_id}/status")
def update_organizer_status(
    organizer_id: str, body: OrganizerStatusUpdate,
    db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin),
):
    org = db.query(Organizer).filter(Organizer.id == organizer_id).first()
    if not org:
        raise HTTPException(404, "Organizer not found")
    org.status = OrganizerStatus(body.status)  # type: ignore
    db.add(AuditLog(
        actor_type="admin", actor_id=admin.id, actor_email=admin.email,
        action=f"organizer.status.{body.status}", resource_type="organizer",
        resource_id=organizer_id, meta={"reason": body.reason},
    ))
    db.commit()
    return {"message": f"Organizer status updated to {body.status}"}


# ── Event Management ──────────────────────────────────────────────────────────

@router.get("/events")
def list_all_events(
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    query = db.query(Event)
    if status:
        query = query.filter(Event.status == EventStatus(status))
    total = query.count()
    events = query.order_by(Event.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"items": events, "total": total, "page": page, "limit": limit}


@router.put("/events/{event_id}/approve")
def approve_event(
    event_id: str, body: EventApproval,
    db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    if body.approved:
        event.status = EventStatus.published  # type: ignore
        event.approved_by = admin.id
        event.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)  # type: ignore
        event.rejection_reason = None  # type: ignore
    else:
        event.status = EventStatus.draft  # type: ignore
        event.rejection_reason = body.rejection_reason  # type: ignore
    db.add(AuditLog(
        actor_type="admin", actor_id=admin.id, actor_email=admin.email,
        action="event.approved" if body.approved else "event.rejected",
        resource_type="event", resource_id=event_id,
        meta={"reason": body.rejection_reason},
    ))
    db.commit()
    return {"message": "Event approved" if body.approved else "Event rejected"}


@router.put("/events/{event_id}/feature")
def feature_event(
    event_id: str, featured: bool,
    db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    event.is_featured = featured  # type: ignore
    db.commit()
    return {"message": f"Event {'featured' if featured else 'unfeatured'}"}


@router.delete("/events/{event_id}")
def remove_event(
    event_id: str, db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    db.add(AuditLog(
        actor_type="admin", actor_id=admin.id, actor_email=admin.email,
        action="event.removed", resource_type="event", resource_id=event_id,
    ))
    db.delete(event)
    db.commit()
    return {"message": "Event removed"}


# ── Event Categories ──────────────────────────────────────────────────────────

@router.post("/categories", response_model=EventCategoryResponse, status_code=201)
def create_category(
    body: EventCategoryCreate,
    db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin),
):
    from sqlalchemy.exc import IntegrityError
    try:
        cat = EventCategory(**body.model_dump())
        db.add(cat)
        db.commit()
        db.refresh(cat)
        return cat
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Category slug already exists")


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: str, db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    cat = db.query(EventCategory).filter(EventCategory.id == category_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    db.delete(cat)
    db.commit()
    return {"message": "Category deleted"}


# ── Financial ─────────────────────────────────────────────────────────────────

@router.get("/orders")
def all_orders(
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin),
):
    total = db.query(Order).count()
    orders = db.query(Order).order_by(Order.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"items": orders, "total": total}


@router.post("/payouts", response_model=PayoutResponse, status_code=201)
def create_payout(
    body: PayoutRequest,
    db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin),
):
    org = db.query(Organizer).filter(Organizer.id == body.organizer_id).first()
    if not org:
        raise HTTPException(404, "Organizer not found")
    payout = OrganizerPayout(
        organizer_id=body.organizer_id,
        amount=body.amount,
        notes=body.notes,
        status=PayoutStatus.pending,
    )
    db.add(payout)
    db.commit()
    db.refresh(payout)
    return payout


@router.put("/payouts/{payout_id}/process")
def process_payout(
    payout_id: str, db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    payout = db.query(OrganizerPayout).filter(OrganizerPayout.id == payout_id).first()
    if not payout:
        raise HTTPException(404, "Payout not found")
    payout.status = PayoutStatus.processed  # type: ignore
    payout.processed_at = datetime.now(timezone.utc).replace(tzinfo=None)  # type: ignore
    db.commit()
    return {"message": "Payout processed"}


# ── Platform Config ───────────────────────────────────────────────────────────

@router.put("/config/commission")
def update_commission(
    body: CommissionUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_super_admin),
):
    setting = db.query(PlatformSettings).filter(PlatformSettings.key == "commission_percent").first()
    if not setting:
        setting = PlatformSettings(key="commission_percent", description="Platform commission %")
        db.add(setting)
    setting.value = str(body.commission_percent)  # type: ignore
    db.add(AuditLog(
        actor_type="admin", actor_id=admin.id, actor_email=admin.email,
        action="config.commission.updated", meta={"new_value": body.commission_percent},
    ))
    db.commit()
    return {"message": f"Commission updated to {body.commission_percent}%"}


# ── Audit Logs ────────────────────────────────────────────────────────────────

@router.get("/audit-logs", response_model=list[AuditLogResponse])
def audit_logs(
    page: int = Query(1, ge=1), limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset((page - 1) * limit).limit(limit).all()


# ── Admin Management ──────────────────────────────────────────────────────────

@router.get("/admins", response_model=list[AdminResponse])
def list_admins(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_super_admin),
):
    return db.query(Admin).all()


@router.put("/admins/{admin_id}/deactivate")
def deactivate_admin(
    admin_id: str, db: Session = Depends(get_db),
    admin: Admin = Depends(get_super_admin),
):
    target = db.query(Admin).filter(Admin.id == admin_id).first()
    if not target:
        raise HTTPException(404, "Admin not found")
    if target.id == admin.id:
        raise HTTPException(400, "Cannot deactivate yourself")
    target.is_active = False  # type: ignore
    db.commit()
    return {"message": "Admin deactivated"}


# ── Config Management ─────────────────────────────────────────────────────────

@router.get("/config")
def list_configs(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return db.query(PlatformSettings).all()


@router.put("/config/{key}")
def update_config_value(
    key: str,
    value: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_super_admin),
):
    setting = db.query(PlatformSettings).filter(PlatformSettings.key == key).first()
    if not setting:
        setting = PlatformSettings(key=key, description=f"Platform config: {key}")
        db.add(setting)
    setting.value = value  # type: ignore
    db.add(AuditLog(
        actor_type="admin", actor_id=admin.id, actor_email=admin.email,
        action=f"config.{key}.updated", meta={"value": value},
    ))
    db.commit()
    return {"message": f"Config {key} updated to: {value}"}


# ── Category Management Update ────────────────────────────────────────────────

@router.put("/categories/{category_id}", response_model=EventCategoryResponse)
def update_category(
    category_id: str,
    body: EventCategoryCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    cat = db.query(EventCategory).filter(EventCategory.id == category_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    cat.name = body.name  # type: ignore
    cat.slug = body.slug  # type: ignore
    cat.icon = body.icon  # type: ignore
    cat.color = body.color  # type: ignore
    db.commit()
    db.refresh(cat)
    return cat


# ── Create Admin Account ──────────────────────────────────────────────────────

@router.post("/create-admin", response_model=AdminResponse, status_code=201)
def create_new_admin(
    body: AdminCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_super_admin),
):
    if db.query(Admin).filter(Admin.email == body.email).first():
        raise HTTPException(400, "Email already registered")
    from app.core.security import hash_password
    new_admin = Admin(
        email=body.email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        is_super=body.is_super,
        email_verified=True,
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    db.add(AuditLog(
        actor_type="admin", actor_id=admin.id, actor_email=admin.email,
        action="admin.created", resource_type="admin", resource_id=new_admin.id,
    ))
    db.commit()
    return new_admin


# ── Resale Monitoring & Approvals ─────────────────────────────────────────────

@router.get("/resale")
def list_resale_listings(
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    query = db.query(ResaleListing)
    if status:
        query = query.filter(ResaleListing.status == ResaleStatus(status))
    total = query.count()
    listings = query.order_by(ResaleListing.listed_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"items": listings, "total": total}


@router.put("/resale/{listing_id}/approve")
def approve_resale_listing(
    listing_id: str,
    body: ResaleApproval,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    listing = db.query(ResaleListing).filter(ResaleListing.id == listing_id).first()
    if not listing:
        raise HTTPException(404, "Listing not found")
    if listing.status != ResaleStatus.pending:
        raise HTTPException(400, f"Listing is not in pending state (status: {listing.status})")

    if body.approved:
        listing.status = ResaleStatus.active  # type: ignore
        # Ticket is already resold status, keep it that way for escrow
    else:
        listing.status = ResaleStatus.removed  # type: ignore
        listing.ticket.status = TicketStatus.active  # type: ignore

    db.add(AuditLog(
        actor_type="admin", actor_id=admin.id, actor_email=admin.email,
        action="resale.approved" if body.approved else "resale.rejected",
        resource_type="resale_listing", resource_id=listing_id,
    ))
    db.commit()
    return {"message": "Resale listing approved" if body.approved else "Resale listing rejected"}


# ── Refund Management ─────────────────────────────────────────────────────────

@router.get("/refunds")
def list_pending_refund_requests(
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    query = db.query(Order).filter(Order.status == OrderStatus.refund_pending)
    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"items": orders, "total": total}


@router.put("/orders/{order_id}/refund")
def process_order_refund(
    order_id: str,
    body: RefundApproval,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.status not in (OrderStatus.confirmed, OrderStatus.refund_pending):
        raise HTTPException(400, f"Order cannot be refunded (status: {order.status})")

    if body.approved:
        order.status = OrderStatus.refunded  # type: ignore
        # Invalidate all tickets and return quantities
        for item in order.items:
            item.ticket_type.quantity_sold = max(0, item.ticket_type.quantity_sold - item.quantity)  # type: ignore
            for ticket in item.tickets:
                ticket.status = TicketStatus.cancelled  # type: ignore
        message = "Refund approved and processed successfully"
    else:
        # Revert back to confirmed if rejected
        order.status = OrderStatus.confirmed  # type: ignore
        message = f"Refund request rejected. Reason: {body.rejection_reason or 'None'}"

    db.add(AuditLog(
        actor_type="admin", actor_id=admin.id, actor_email=admin.email,
        action="order.refund_approved" if body.approved else "order.refund_rejected",
        resource_type="order", resource_id=order_id,
        meta={"reason": body.rejection_reason},
    ))
    db.commit()
    return {"message": message}


# ── Admin Analytics ───────────────────────────────────────────────────────────

@router.get("/analytics")
def platform_analytics(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    # Dialect-safe date grouping (PostgreSQL to_char vs SQLite strftime)
    is_postgres = db.bind.dialect.name == "postgresql"
    org_date_expr = func.to_char(Organizer.created_at, "YYYY-MM") if is_postgres else func.strftime("%Y-%m", Organizer.created_at)
    order_date_expr = func.to_char(Order.created_at, "YYYY-MM") if is_postgres else func.strftime("%Y-%m", Order.created_at)

    # Growth metrics: organizers registered per month
    organizers_growth = db.query(
        org_date_expr.label("month"),
        func.count(Organizer.id).label("count")
    ).group_by("month").order_by("month").all()

    # Sales metrics: orders per month
    sales_growth = db.query(
        order_date_expr.label("month"),
        func.count(Order.id).label("count"),
        func.sum(Order.total_amount).label("revenue")
    ).filter(Order.status == OrderStatus.confirmed).group_by("month").order_by("month").all()


    # Top-performing events (by revenue)
    top_events = db.query(
        Event.id, Event.title,
        func.sum(Order.total_amount).label("revenue"),
        func.sum(OrderItem.quantity).label("tickets_sold")
    ).join(Order, Order.event_id == Event.id)\
     .join(OrderItem, OrderItem.order_id == Order.id)\
     .filter(Order.status == OrderStatus.confirmed)\
     .group_by(Event.id, Event.title)\
     .order_by(func.sum(Order.total_amount).desc()).limit(5).all()

    # Resale marketplace activity
    total_listed = db.query(ResaleListing).count()
    total_sold = db.query(ResaleListing).filter(ResaleListing.status == ResaleStatus.sold).count()
    resale_revenue = db.query(func.sum(ResaleListing.asking_price))\
                       .filter(ResaleListing.status == ResaleStatus.sold).scalar() or Decimal("0.00")

    return {
        "organizer_growth": [{"month": r[0], "count": r[1]} for r in organizers_growth],
        "sales_growth": [{"month": r[0], "orders": r[1], "revenue": float(r[2] or 0)} for r in sales_growth],
        "top_events": [{"id": r[0], "title": r[1], "revenue": float(r[2] or 0), "tickets_sold": int(r[3] or 0)} for r in top_events],
        "resale_activity": {
            "total_listed": total_listed,
            "total_sold": total_sold,
            "resale_revenue": float(resale_revenue),
        }
    }
