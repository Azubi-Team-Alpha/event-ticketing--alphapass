"""Public + organizer event management routes."""
from decimal import Decimal
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.base import get_db
from app.models.models import Event, EventCategory, EventStatus, TicketType, Organizer
from app.schemas.schemas import (
    EventCreate, EventUpdate, EventResponse, EventListResponse, EventListItem,
    EventCategoryCreate, EventCategoryResponse,
    TicketTypeCreate, TicketTypeUpdate, TicketTypeResponse,
    PromoCodeCreate, PromoCodeResponse,
)
from app.core.dependencies import get_current_organizer, get_active_organizer, get_current_admin, get_current_user

router = APIRouter()


def _build_list_item(event: Event) -> EventListItem:
    prices = [tt.price for tt in event.ticket_types if tt.is_active]
    return EventListItem(
        id=event.id, title=event.title,
        banner_image_url=event.banner_image_url, thumbnail_url=event.thumbnail_url,
        venue_name=event.venue_name, city=event.city, country=event.country,
        is_online=event.is_online, starts_at=event.starts_at, ends_at=event.ends_at,
        status=event.status.value if hasattr(event.status, 'value') else event.status,
        is_featured=event.is_featured,
        category=event.category,
        min_price=min(prices) if prices else Decimal("0.00"),
        max_price=max(prices) if prices else Decimal("0.00"),
        total_capacity=event.total_capacity,
        total_sold=event.total_sold,
    )


# ── Public: Browse Events ─────────────────────────────────────────────────────

@router.get("/categories", response_model=list[EventCategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(EventCategory).all()


@router.get("", response_model=EventListResponse)
def list_events(
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    category: str | None = Query(None),
    city: str | None = Query(None),
    search: str | None = Query(None),
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Event).filter(Event.status == EventStatus.published)

    if category:
        query = query.join(EventCategory).filter(
            or_(EventCategory.slug == category, EventCategory.id == category)
        )
    if city:
        query = query.filter(Event.city.ilike(f"%{city}%"))
    if search:
        query = query.filter(
            or_(Event.title.ilike(f"%{search}%"), Event.description.ilike(f"%{search}%"))
        )
    if min_price is not None:
        query = query.filter(Event.ticket_types.any(TicketType.price >= min_price))
    if max_price is not None:
        query = query.filter(Event.ticket_types.any(TicketType.price <= max_price))
    if date_from:
        try:
            df = datetime.fromisoformat(date_from)
            query = query.filter(Event.starts_at >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.filter(Event.starts_at <= dt)
        except ValueError:
            pass

    total = query.count()
    events = query.order_by(Event.is_featured.desc(), Event.starts_at).offset((page - 1) * limit).limit(limit).all()
    return EventListResponse(items=[_build_list_item(e) for e in events], total=total, page=page, limit=limit)


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    if event.status not in (EventStatus.published,):
        raise HTTPException(404, "Event not found")
    return event


# ── Organizer: Event CRUD ─────────────────────────────────────────────────────

@router.get("/organizer/my-events", response_model=EventListResponse)
def organizer_my_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    org: Organizer = Depends(get_current_organizer),
):
    query = db.query(Event).filter(Event.organizer_id == org.id)
    total = query.count()
    events = query.order_by(Event.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return EventListResponse(items=[_build_list_item(e) for e in events], total=total, page=page, limit=limit)


@router.post("/organizer", response_model=EventResponse, status_code=201)
def create_event(
    body: EventCreate, db: Session = Depends(get_db),
    org: Organizer = Depends(get_active_organizer),
):
    if body.category_id:
        if not db.query(EventCategory).filter(EventCategory.id == body.category_id).first():
            raise HTTPException(404, "Category not found")

    data = body.model_dump()
    event = Event(**data, organizer_id=org.id)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/organizer/{event_id}", response_model=EventResponse)
def get_organizer_event(
    event_id: str, db: Session = Depends(get_db),
    org: Organizer = Depends(get_current_organizer),
):
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == org.id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    return event


@router.put("/organizer/{event_id}", response_model=EventResponse)
def update_event(
    event_id: str, body: EventUpdate, db: Session = Depends(get_db),
    org: Organizer = Depends(get_active_organizer),
):
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == org.id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    if event.status == EventStatus.cancelled:
        raise HTTPException(400, "Cannot edit a cancelled event")

    data = body.model_dump(exclude_unset=True)
    is_published = data.pop("is_published", None)
    if is_published is not None:
        if is_published and not event.ticket_types:
            raise HTTPException(400, "Event must have at least one ticket type before publishing")
        event.status = EventStatus.published if is_published else EventStatus.draft

    for field, value in data.items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return event


@router.post("/organizer/{event_id}/publish", response_model=EventResponse)
def publish_event(
    event_id: str, db: Session = Depends(get_db),
    org: Organizer = Depends(get_active_organizer),
):
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == org.id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    if not event.ticket_types:
        raise HTTPException(400, "Event must have at least one ticket type before publishing")
    from app.core.config import settings as _s
    target = EventStatus.pending if _s.REQUIRE_EVENT_APPROVAL else EventStatus.published
    event.status = target
    db.commit()
    db.refresh(event)
    return event


@router.post("/organizer/{event_id}/unpublish", response_model=EventResponse)
def unpublish_event(
    event_id: str, db: Session = Depends(get_db),
    org: Organizer = Depends(get_active_organizer),
):
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == org.id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    event.status = EventStatus.draft
    db.commit()
    db.refresh(event)
    return event


@router.post("/organizer/{event_id}/cancel", response_model=EventResponse)
def cancel_event(
    event_id: str, db: Session = Depends(get_db),
    org: Organizer = Depends(get_active_organizer),
):
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == org.id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    event.status = EventStatus.cancelled
    db.commit()
    db.refresh(event)
    return event


@router.post("/organizer/{event_id}/duplicate", response_model=EventResponse, status_code=201)
def duplicate_event(
    event_id: str, db: Session = Depends(get_db),
    org: Organizer = Depends(get_active_organizer),
):
    src = db.query(Event).filter(Event.id == event_id, Event.organizer_id == org.id).first()
    if not src:
        raise HTTPException(404, "Event not found")

    new_event = Event(
        organizer_id=org.id, category_id=src.category_id,
        title=f"[Copy] {src.title}", description=src.description,
        policies=src.policies, venue_name=src.venue_name, address=src.address,
        city=src.city, country=src.country, is_online=src.is_online,
        online_url=src.online_url, starts_at=src.starts_at, ends_at=src.ends_at,
        allow_transfers=src.allow_transfers, allow_resale=src.allow_resale,
        group_discount_threshold=src.group_discount_threshold,
        group_discount_percent=src.group_discount_percent,
        allow_refunds=src.allow_refunds,
        status=EventStatus.draft,
    )
    db.add(new_event)
    db.flush()

    for tt in src.ticket_types:
        db.add(TicketType(
            event_id=new_event.id, name=tt.name, description=tt.description,
            benefits=tt.benefits, price=tt.price, quantity=tt.quantity,
            purchase_limit=tt.purchase_limit, min_purchase=tt.min_purchase,
            sales_start=tt.sales_start, sales_end=tt.sales_end, sort_order=tt.sort_order,
        ))

    db.commit()
    db.refresh(new_event)
    return new_event


@router.post("/organizer/{event_id}/archive", response_model=EventResponse)
def archive_event(
    event_id: str, db: Session = Depends(get_db),
    org: Organizer = Depends(get_active_organizer),
):
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == org.id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    event.status = EventStatus.archived
    db.commit()
    db.refresh(event)
    return event


# ── Ticket Types ──────────────────────────────────────────────────────────────

@router.post("/organizer/{event_id}/ticket-types", response_model=TicketTypeResponse, status_code=201)
def create_ticket_type(
    event_id: str, body: TicketTypeCreate, db: Session = Depends(get_db),
    org: Organizer = Depends(get_active_organizer),
):
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == org.id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    tt = TicketType(**body.model_dump(), event_id=event_id)
    db.add(tt)
    db.commit()
    db.refresh(tt)
    return tt


@router.put("/organizer/{event_id}/ticket-types/{tt_id}", response_model=TicketTypeResponse)
def update_ticket_type(
    event_id: str, tt_id: str, body: TicketTypeUpdate,
    db: Session = Depends(get_db), org: Organizer = Depends(get_active_organizer),
):
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == org.id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    tt = db.query(TicketType).filter(TicketType.id == tt_id, TicketType.event_id == event_id).first()
    if not tt:
        raise HTTPException(404, "Ticket type not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tt, field, value)
    db.commit()
    db.refresh(tt)
    return tt


@router.delete("/organizer/{event_id}/ticket-types/{tt_id}")
def delete_ticket_type(
    event_id: str, tt_id: str, db: Session = Depends(get_db),
    org: Organizer = Depends(get_active_organizer),
):
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == org.id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    tt = db.query(TicketType).filter(TicketType.id == tt_id, TicketType.event_id == event_id).first()
    if not tt:
        raise HTTPException(404, "Ticket type not found")
    if tt.quantity_sold > 0:
        raise HTTPException(400, "Cannot delete a ticket type with sold tickets")
    db.delete(tt)
    db.commit()
    return {"message": "Ticket type deleted"}


# ── Promo Codes ───────────────────────────────────────────────────────────────

@router.post("/organizer/{event_id}/promo-codes", response_model=PromoCodeResponse, status_code=201)
def create_promo_code(
    event_id: str, body: PromoCodeCreate, db: Session = Depends(get_db),
    org: Organizer = Depends(get_active_organizer),
):
    from app.models.models import PromoCode, DiscountType
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == org.id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    from sqlalchemy.exc import IntegrityError
    try:
        code = PromoCode(
            event_id=event_id, organizer_id=org.id,
            code=body.code.upper(), discount_type=DiscountType(body.discount_type),
            discount_value=body.discount_value, max_uses=body.max_uses,
            applicable_ticket_type_ids=body.applicable_ticket_type_ids,
            expires_at=body.expires_at,
        )
        db.add(code)
        db.commit()
        db.refresh(code)
        return code
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Promo code already exists for this event")


@router.get("/organizer/{event_id}/promo-codes", response_model=list[PromoCodeResponse])
def list_promo_codes(
    event_id: str, db: Session = Depends(get_db),
    org: Organizer = Depends(get_active_organizer),
):
    from app.models.models import PromoCode
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == org.id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    return db.query(PromoCode).filter(PromoCode.event_id == event_id).all()


# ── Compatibility & Registration Endpoints ────────────────────────────────────

@router.post("", response_model=EventResponse, status_code=201)
def create_event_compatibility(
    body: EventCreate, db: Session = Depends(get_db),
    org: Organizer = Depends(get_active_organizer),
):
    return create_event(body, db, org)


@router.put("/{event_id}", response_model=EventResponse)
def update_event_compatibility(
    event_id: str, body: EventUpdate, db: Session = Depends(get_db),
    org: Organizer = Depends(get_active_organizer),
):
    return update_event(event_id, body, db, org)


@router.delete("/{event_id}")
def delete_event_compatibility(
    event_id: str, db: Session = Depends(get_db),
    org: Organizer = Depends(get_current_organizer),
):
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == org.id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    db.query(TicketType).filter(TicketType.event_id == event_id).delete()
    db.delete(event)
    db.commit()
    return {"message": "Event deleted"}


@router.get("/admin/all")
def list_admin_all_events(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin),
):
    query = db.query(Event)
    if status:
        query = query.filter(Event.status == EventStatus(status))
    total = query.count()
    events = query.order_by(Event.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    items = [_build_list_item(e) for e in events]
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.post("/{event_id}/register", status_code=201)
def register_user_for_event(
    event_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    from app.models.models import Order, OrderStatus, OrderItem, Ticket, TicketStatus
    from app.routers.orders import _generate_qr_codes, _send_order_confirmation

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event or event.status != EventStatus.published:
        raise HTTPException(404, "Event not found or not available")

    # Select ticket type with row lock to avoid race conditions
    tt = db.query(TicketType).filter(
        TicketType.event_id == event_id,
        TicketType.is_active == True,
    ).with_for_update().order_by(TicketType.sort_order).first()

    if not tt:
        raise HTTPException(400, "No active ticket types found for this event")

    if tt.quantity_remaining < 1:
        raise HTTPException(400, "Ticket type is sold out")

    order = Order(
        event_id=event_id,
        guest_name=current_user.full_name,
        guest_email=current_user.email,
        status=OrderStatus.confirmed,
        subtotal=tt.price,
        discount_amount=Decimal("0.00"),
        platform_fee=Decimal("0.00"),
        total_amount=tt.price,
    )
    db.add(order)
    db.flush()

    oi = OrderItem(
        order_id=order.id,
        ticket_type_id=tt.id,
        quantity=1,
        unit_price=tt.price,
        line_total=tt.price,
    )
    db.add(oi)
    db.flush()

    ticket = Ticket(
        order_item_id=oi.id,
        attendee_name=current_user.full_name,
        attendee_email=current_user.email,
        status=TicketStatus.active,
    )
    db.add(ticket)
    db.flush()

    tt.quantity_sold += 1
    db.commit()
    db.refresh(order)

    background_tasks.add_task(_generate_qr_codes, [ticket.id])
    background_tasks.add_task(
        _send_order_confirmation,
        order.guest_email, order.guest_name, event.title,
        order.id, 1, str(order.total_amount),
    )

    return {"message": "Registered successfully", "order_id": order.id}

