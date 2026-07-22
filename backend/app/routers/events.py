"""Public + organizer event management routes using DynamoDB."""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

from app.db.dynamodb import dynamodb_helper
from app.schemas.schemas import (
    EventCreate, EventUpdate, EventResponse, EventListResponse, EventListItem,
    EventCategoryCreate, EventCategoryResponse,
    TicketTypeCreate, TicketTypeUpdate, TicketTypeResponse,
    PromoCodeCreate, PromoCodeResponse,
)
from app.core.dependencies import get_current_organizer, get_active_organizer, get_current_admin, get_current_user, AttrDict
from app.core.config import settings

router = APIRouter()


def _format_dt(val: Any) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        dt = datetime.fromisoformat(str(val))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _format_event_response(e: Dict[str, Any]) -> Dict[str, Any]:
    event_id = e.get("EventID") or e.get("id")
    ticket_types = e.get("ticket_types", [])
    
    formatted_tts = []
    for tt in ticket_types:
        tt_id = tt.get("id") or str(uuid.uuid4())
        formatted_tts.append({
            "id": tt_id,
            "event_id": event_id,
            "name": tt.get("name", "Standard"),
            "description": tt.get("description"),
            "benefits": tt.get("benefits", []),
            "price": Decimal(str(tt.get("price", 0))),
            "quantity": int(tt.get("quantity", 0)),
            "quantity_sold": int(tt.get("quantity_sold", 0)),
            "purchase_limit": int(tt.get("purchase_limit", 10)),
            "min_purchase": int(tt.get("min_purchase", 1)),
            "sales_start": _format_dt(tt.get("sales_start")),
            "sales_end": _format_dt(tt.get("sales_end")),
            "is_active": tt.get("is_active", True),
            "sort_order": int(tt.get("sort_order", 0)),
            "quantity_remaining": max(0, int(tt.get("quantity", 0)) - int(tt.get("quantity_sold", 0))),
            "is_sold_out": max(0, int(tt.get("quantity", 0)) - int(tt.get("quantity_sold", 0))) <= 0,
            "created_at": _format_dt(tt.get("created_at")) or datetime.now(timezone.utc),
        })

    cat = e.get("category")
    if isinstance(cat, dict):
        cat_resp = {
            "id": cat.get("CategoryID") or cat.get("id", ""),
            "name": cat.get("name", ""),
            "slug": cat.get("slug", ""),
            "icon": cat.get("icon"),
            "sort_order": int(cat.get("sort_order", 0)),
        }
    else:
        cat_resp = None

    return {
        "id": event_id,
        "organizer_id": e.get("organizer_id", ""),
        "category_id": e.get("category_id"),
        "title": e.get("title", ""),
        "description": e.get("description"),
        "policies": e.get("policies"),
        "banner_image_url": e.get("banner_image_url"),
        "thumbnail_url": e.get("thumbnail_url"),
        "venue_name": e.get("venue_name"),
        "address": e.get("address"),
        "city": e.get("city"),
        "country": e.get("country", "Ghana"),
        "is_online": e.get("is_online", False),
        "online_url": e.get("online_url"),
        "starts_at": _format_dt(e.get("starts_at")) or datetime.now(timezone.utc),
        "ends_at": _format_dt(e.get("ends_at")),
        "status": e.get("status", "published"),
        "rejection_reason": e.get("rejection_reason"),
        "is_featured": e.get("is_featured", False),
        "allow_transfers": e.get("allow_transfers", True),
        "transfer_deadline_hours": int(e.get("transfer_deadline_hours", 24)),
        "max_transfers_per_ticket": int(e.get("max_transfers_per_ticket", 1)),
        "allow_resale": e.get("allow_resale", True),
        "max_resale_markup_percent": Decimal(str(e.get("max_resale_markup_percent", "10.00"))),
        "group_discount_threshold": e.get("group_discount_threshold"),
        "group_discount_percent": Decimal(str(e.get("group_discount_percent"))) if e.get("group_discount_percent") else None,
        "allow_refunds": e.get("allow_refunds", True),
        "refund_policy_notes": e.get("refund_policy_notes"),
        "created_at": _format_dt(e.get("created_at")) or datetime.now(timezone.utc),
        "updated_at": _format_dt(e.get("updated_at")) or datetime.now(timezone.utc),
        "approved_at": _format_dt(e.get("approved_at")),
        "category": cat_resp,
        "ticket_types": formatted_tts,
        "total_capacity": sum(tt["quantity"] for tt in formatted_tts),
        "total_sold": sum(tt["quantity_sold"] for tt in formatted_tts),
    }


def _build_list_item(e: Dict[str, Any]) -> EventListItem:
    formatted = _format_event_response(e)
    prices = [tt["price"] for tt in formatted["ticket_types"] if tt.get("is_active", True)]
    
    cat = formatted.get("category")
    cat_obj = EventCategoryResponse(**cat) if cat else None

    return EventListItem(
        id=formatted["id"],
        title=formatted["title"],
        banner_image_url=formatted["banner_image_url"],
        thumbnail_url=formatted["thumbnail_url"],
        venue_name=formatted["venue_name"],
        city=formatted["city"],
        country=formatted["country"],
        is_online=formatted["is_online"],
        starts_at=formatted["starts_at"],
        ends_at=formatted["ends_at"],
        status=formatted["status"],
        is_featured=formatted["is_featured"],
        category=cat_obj,
        min_price=min(prices) if prices else Decimal("0.00"),
        max_price=max(prices) if prices else Decimal("0.00"),
        total_capacity=formatted["total_capacity"],
        total_sold=formatted["total_sold"],
    )


# ── Public: Browse Events ─────────────────────────────────────────────────────

@router.get("/categories", response_model=list[EventCategoryResponse])
def list_categories():
    raw_cats = dynamodb_helper.list_categories()
    return [
        EventCategoryResponse(
            id=c.get("CategoryID") or c.get("id", ""),
            name=c.get("name", ""),
            slug=c.get("slug", ""),
            icon=c.get("icon"),
            sort_order=int(c.get("sort_order", 0)),
        )
        for c in raw_cats
    ]


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
):
    raw_events = dynamodb_helper.list_events_by_status("published")
    filtered = []
    
    for e in raw_events:
        fmt = _format_event_response(e)
        
        if category:
            cat_match = False
            cat_obj = fmt.get("category")
            if cat_obj and (cat_obj.get("slug") == category or cat_obj.get("id") == category):
                cat_match = True
            if not cat_match and e.get("category_id") == category:
                cat_match = True
            if not cat_match:
                continue

        if city and fmt.get("city"):
            if city.lower() not in fmt["city"].lower():
                continue

        if search:
            s = search.lower()
            title = (fmt.get("title") or "").lower()
            desc = (fmt.get("description") or "").lower()
            if s not in title and s not in desc:
                continue

        prices = [tt["price"] for tt in fmt["ticket_types"] if tt.get("is_active", True)]
        min_p = min(prices) if prices else Decimal("0.00")
        max_p = max(prices) if prices else Decimal("0.00")

        if min_price is not None and max_p < Decimal(str(min_price)):
            continue
        if max_price is not None and min_p > Decimal(str(max_price)):
            continue

        if date_from:
            try:
                df = datetime.fromisoformat(date_from)
                if df.tzinfo is None:
                    df = df.replace(tzinfo=timezone.utc)
                if fmt["starts_at"] < df:
                    continue
            except ValueError:
                pass

        if date_to:
            try:
                dt = datetime.fromisoformat(date_to)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if fmt["starts_at"] > dt:
                    continue
            except ValueError:
                pass

        filtered.append(e)

    # Sort featured first, then by starts_at
    filtered.sort(key=lambda x: (not x.get("is_featured", False), x.get("starts_at", "")))
    
    total = len(filtered)
    start_idx = (page - 1) * limit
    page_items = filtered[start_idx : start_idx + limit]

    return EventListResponse(
        items=[_build_list_item(e) for e in page_items],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: str):
    e = dynamodb_helper.get_event(event_id)
    if not e:
        raise HTTPException(404, "Event not found")
    if e.get("status") not in ("published",):
        raise HTTPException(404, "Event not found")
    return _format_event_response(e)


# ── Organizer: Event CRUD ─────────────────────────────────────────────────────

@router.get("/organizer/my-events", response_model=EventListResponse)
def organizer_my_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    org: AttrDict = Depends(get_current_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    events = dynamodb_helper.list_events_by_organizer(org_id)
    events.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    total = len(events)
    start_idx = (page - 1) * limit
    page_items = events[start_idx : start_idx + limit]

    return EventListResponse(
        items=[_build_list_item(e) for e in page_items],
        total=total,
        page=page,
        limit=limit,
    )


@router.post("/organizer", response_model=EventResponse, status_code=201)
def create_event(
    body: EventCreate,
    org: AttrDict = Depends(get_active_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    event_id = str(uuid.uuid4())
    data = body.model_dump()
    
    if data.get("category_id"):
        cat = dynamodb_helper.get_category(data["category_id"])
        if not cat:
            raise HTTPException(404, "Category not found")
        data["category"] = cat

    data["organizer_id"] = org_id
    data["status"] = "draft"
    data["ticket_types"] = []
    
    created = dynamodb_helper.create_event(event_id, data)
    return _format_event_response(created)


@router.get("/organizer/{event_id}", response_model=EventResponse)
def get_organizer_event(
    event_id: str,
    org: AttrDict = Depends(get_current_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    e = dynamodb_helper.get_event(event_id)
    if not e or e.get("organizer_id") != org_id:
        raise HTTPException(404, "Event not found")
    return _format_event_response(e)


@router.put("/organizer/{event_id}", response_model=EventResponse)
def update_event(
    event_id: str,
    body: EventUpdate,
    org: AttrDict = Depends(get_active_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    e = dynamodb_helper.get_event(event_id)
    if not e or e.get("organizer_id") != org_id:
        raise HTTPException(404, "Event not found")
    if e.get("status") == "cancelled":
        raise HTTPException(400, "Cannot edit a cancelled event")

    data = body.model_dump(exclude_unset=True)
    is_published = data.pop("is_published", None)
    if is_published is not None:
        if is_published and not e.get("ticket_types"):
            raise HTTPException(400, "Event must have at least one ticket type before publishing")
        data["status"] = "published" if is_published else "draft"

    updated = dynamodb_helper.update_event(event_id, data) or e
    return _format_event_response(updated)


@router.post("/organizer/{event_id}/publish", response_model=EventResponse)
def publish_event(
    event_id: str,
    org: AttrDict = Depends(get_active_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    e = dynamodb_helper.get_event(event_id)
    if not e or e.get("organizer_id") != org_id:
        raise HTTPException(404, "Event not found")
    if not e.get("ticket_types"):
        raise HTTPException(400, "Event must have at least one ticket type before publishing")

    target = "pending" if settings.REQUIRE_EVENT_APPROVAL else "published"
    updated = dynamodb_helper.update_event(event_id, {"status": target}) or e
    return _format_event_response(updated)


@router.post("/organizer/{event_id}/unpublish", response_model=EventResponse)
def unpublish_event(
    event_id: str,
    org: AttrDict = Depends(get_active_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    e = dynamodb_helper.get_event(event_id)
    if not e or e.get("organizer_id") != org_id:
        raise HTTPException(404, "Event not found")
    updated = dynamodb_helper.update_event(event_id, {"status": "draft"}) or e
    return _format_event_response(updated)


@router.post("/organizer/{event_id}/cancel", response_model=EventResponse)
def cancel_event(
    event_id: str,
    org: AttrDict = Depends(get_active_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    e = dynamodb_helper.get_event(event_id)
    if not e or e.get("organizer_id") != org_id:
        raise HTTPException(404, "Event not found")
    updated = dynamodb_helper.update_event(event_id, {"status": "cancelled"}) or e
    return _format_event_response(updated)


@router.post("/organizer/{event_id}/duplicate", response_model=EventResponse, status_code=201)
def duplicate_event(
    event_id: str,
    org: AttrDict = Depends(get_active_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    src = dynamodb_helper.get_event(event_id)
    if not src or src.get("organizer_id") != org_id:
        raise HTTPException(404, "Event not found")

    new_id = str(uuid.uuid4())
    tts = []
    for tt in src.get("ticket_types", []):
        tts.append({
            "id": str(uuid.uuid4()),
            "name": tt.get("name"),
            "description": tt.get("description"),
            "benefits": tt.get("benefits"),
            "price": tt.get("price"),
            "quantity": tt.get("quantity"),
            "quantity_sold": 0,
            "purchase_limit": tt.get("purchase_limit", 10),
            "min_purchase": tt.get("min_purchase", 1),
            "is_active": True,
        })

    new_event_data = {
        "organizer_id": org_id,
        "category_id": src.get("category_id"),
        "title": f"[Copy] {src.get('title')}",
        "description": src.get("description"),
        "policies": src.get("policies"),
        "venue_name": src.get("venue_name"),
        "address": src.get("address"),
        "city": src.get("city"),
        "country": src.get("country"),
        "is_online": src.get("is_online", False),
        "online_url": src.get("online_url"),
        "starts_at": src.get("starts_at"),
        "ends_at": src.get("ends_at"),
        "allow_transfers": src.get("allow_transfers", True),
        "allow_resale": src.get("allow_resale", True),
        "group_discount_threshold": src.get("group_discount_threshold"),
        "group_discount_percent": src.get("group_discount_percent"),
        "allow_refunds": src.get("allow_refunds", True),
        "status": "draft",
        "ticket_types": tts,
    }
    
    created = dynamodb_helper.create_event(new_id, new_event_data)
    return _format_event_response(created)


@router.post("/organizer/{event_id}/archive", response_model=EventResponse)
def archive_event(
    event_id: str,
    org: AttrDict = Depends(get_active_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    e = dynamodb_helper.get_event(event_id)
    if not e or e.get("organizer_id") != org_id:
        raise HTTPException(404, "Event not found")
    updated = dynamodb_helper.update_event(event_id, {"status": "archived"}) or e
    return _format_event_response(updated)


# ── Ticket Types ──────────────────────────────────────────────────────────────

@router.post("/organizer/{event_id}/ticket-types", response_model=TicketTypeResponse, status_code=201)
def create_ticket_type(
    event_id: str,
    body: TicketTypeCreate,
    org: AttrDict = Depends(get_active_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    e = dynamodb_helper.get_event(event_id)
    if not e or e.get("organizer_id") != org_id:
        raise HTTPException(404, "Event not found")

    tt_id = str(uuid.uuid4())
    new_tt = {
        "id": tt_id,
        "name": body.name,
        "description": body.description,
        "benefits": body.benefits,
        "price": str(body.price),
        "quantity": body.quantity,
        "quantity_sold": 0,
        "purchase_limit": body.purchase_limit,
        "min_purchase": body.min_purchase,
        "sales_start": body.sales_start.isoformat() if body.sales_start else None,
        "sales_end": body.sales_end.isoformat() if body.sales_end else None,
        "is_active": True,
        "sort_order": body.sort_order,
    }
    
    tts = e.get("ticket_types", [])
    tts.append(new_tt)
    dynamodb_helper.update_event(event_id, {"ticket_types": tts})

    return TicketTypeResponse(
        id=tt_id,
        event_id=event_id,
        name=body.name,
        description=body.description,
        benefits=body.benefits,
        price=body.price,
        quantity=body.quantity,
        quantity_sold=0,
        purchase_limit=body.purchase_limit,
        min_purchase=body.min_purchase,
        sales_start=body.sales_start,
        sales_end=body.sales_end,
        is_active=True,
        sort_order=body.sort_order,
        quantity_remaining=body.quantity,
        created_at=datetime.now(timezone.utc),
    )


@router.put("/organizer/{event_id}/ticket-types/{tt_id}", response_model=TicketTypeResponse)
def update_ticket_type(
    event_id: str,
    tt_id: str,
    body: TicketTypeUpdate,
    org: AttrDict = Depends(get_active_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    e = dynamodb_helper.get_event(event_id)
    if not e or e.get("organizer_id") != org_id:
        raise HTTPException(404, "Event not found")

    tts = e.get("ticket_types", [])
    found = None
    for tt in tts:
        if tt.get("id") == tt_id:
            found = tt
            break
    if not found:
        raise HTTPException(404, "Ticket type not found")

    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        if isinstance(v, Decimal):
            v = str(v)
        elif isinstance(v, datetime):
            v = v.isoformat()
        found[k] = v

    dynamodb_helper.update_event(event_id, {"ticket_types": tts})
    
    qty = found.get("quantity", 0)
    sold = found.get("quantity_sold", 0)
    return TicketTypeResponse(
        id=tt_id,
        event_id=event_id,
        name=found["name"],
        description=found.get("description"),
        benefits=found.get("benefits"),
        price=Decimal(str(found["price"])),
        quantity=qty,
        quantity_sold=sold,
        purchase_limit=found.get("purchase_limit", 10),
        min_purchase=found.get("min_purchase", 1),
        sales_start=_format_dt(found.get("sales_start")),
        sales_end=_format_dt(found.get("sales_end")),
        is_active=found.get("is_active", True),
        sort_order=found.get("sort_order", 0),
        quantity_remaining=max(0, qty - sold),
        created_at=_format_dt(found.get("created_at")) or datetime.now(timezone.utc),
    )


@router.delete("/organizer/{event_id}/ticket-types/{tt_id}")
def delete_ticket_type(
    event_id: str,
    tt_id: str,
    org: AttrDict = Depends(get_active_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    e = dynamodb_helper.get_event(event_id)
    if not e or e.get("organizer_id") != org_id:
        raise HTTPException(404, "Event not found")

    tts = e.get("ticket_types", [])
    found = None
    for tt in tts:
        if tt.get("id") == tt_id:
            found = tt
            break
    if not found:
        raise HTTPException(404, "Ticket type not found")

    if found.get("quantity_sold", 0) > 0:
        raise HTTPException(400, "Cannot delete a ticket type with sold tickets")

    tts = [tt for tt in tts if tt.get("id") != tt_id]
    dynamodb_helper.update_event(event_id, {"ticket_types": tts})
    return {"message": "Ticket type deleted"}


# ── Promo Codes ───────────────────────────────────────────────────────────────

@router.post("/organizer/{event_id}/promo-codes", response_model=PromoCodeResponse, status_code=201)
def create_promo_code(
    event_id: str,
    body: PromoCodeCreate,
    org: AttrDict = Depends(get_active_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    e = dynamodb_helper.get_event(event_id)
    if not e or e.get("organizer_id") != org_id:
        raise HTTPException(404, "Event not found")

    code_str = body.code.upper()
    existing = dynamodb_helper.get_promo_code(code_str)
    if existing and existing.get("event_id") == event_id:
        raise HTTPException(400, "Promo code already exists for this event")

    created = dynamodb_helper.create_promo_code(code_str, {
        "event_id": event_id,
        "organizer_id": org_id,
        "discount_type": body.discount_type,
        "discount_value": str(body.discount_value),
        "max_uses": body.max_uses,
        "used_count": 0,
        "applicable_ticket_type_ids": body.applicable_ticket_type_ids,
        "expires_at": body.expires_at.isoformat() if body.expires_at else None,
        "is_active": True,
    })

    return PromoCodeResponse(
        id=code_str,
        event_id=event_id,
        code=code_str,
        discount_type=body.discount_type,
        discount_value=body.discount_value,
        max_uses=body.max_uses,
        used_count=0,
        applicable_ticket_type_ids=body.applicable_ticket_type_ids,
        expires_at=body.expires_at,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@router.get("/organizer/{event_id}/promo-codes", response_model=list[PromoCodeResponse])
def list_promo_codes(
    event_id: str,
    org: AttrDict = Depends(get_active_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    e = dynamodb_helper.get_event(event_id)
    if not e or e.get("organizer_id") != org_id:
        raise HTTPException(404, "Event not found")

    codes = dynamodb_helper.list_promo_codes_by_event(event_id)
    return [
        PromoCodeResponse(
            id=c.get("Code", ""),
            event_id=c.get("event_id", event_id),
            code=c.get("Code", ""),
            discount_type=c.get("discount_type", "percentage"),
            discount_value=Decimal(str(c.get("discount_value", 0))),
            max_uses=c.get("max_uses"),
            used_count=int(c.get("used_count", 0)),
            applicable_ticket_type_ids=c.get("applicable_ticket_type_ids"),
            expires_at=_format_dt(c.get("expires_at")),
            is_active=c.get("is_active", True),
            created_at=_format_dt(c.get("created_at")) or datetime.now(timezone.utc),
        )
        for c in codes
    ]


# ── Compatibility Endpoints ───────────────────────────────────────────────────

@router.post("", response_model=EventResponse, status_code=201)
def create_event_compatibility(
    body: EventCreate,
    org: AttrDict = Depends(get_active_organizer),
):
    return create_event(body, org)


@router.put("/{event_id}", response_model=EventResponse)
def update_event_compatibility(
    event_id: str,
    body: EventUpdate,
    org: AttrDict = Depends(get_active_organizer),
):
    return update_event(event_id, body, org)


@router.delete("/{event_id}")
def delete_event_compatibility(
    event_id: str,
    org: AttrDict = Depends(get_current_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    e = dynamodb_helper.get_event(event_id)
    if not e or e.get("organizer_id") != org_id:
        raise HTTPException(404, "Event not found")

    dynamodb_helper.delete_event(event_id)
    return {"message": "Event deleted"}
