"""Platform Administrator routes using DynamoDB."""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.dynamodb import dynamodb_helper
from app.schemas.schemas import (
    PlatformStats, OrganizerAdminResponse, OrganizerStatusUpdate,
    EventApproval, AdminResponse, PayoutRequest, PayoutResponse,
    EventCategoryCreate, EventCategoryResponse, CommissionUpdate, AuditLogResponse,
    AdminCreate, RefundApproval, ResaleApproval,
)
from app.core.security import hash_password
from app.core.dependencies import get_current_admin, get_super_admin, AttrDict
from app.core.utils import format_dt as _format_dt

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=PlatformStats)
def platform_dashboard(admin: AttrDict = Depends(get_current_admin)):
    orgs = dynamodb_helper.list_organizers()
    total_organizers = len(orgs)
    active_organizers = sum(1 for o in orgs if o.get("status") in ("active", "verified"))

    events = dynamodb_helper.list_events()
    total_events = len(events)
    published_events = sum(1 for e in events if e.get("status") == "published")

    orders = dynamodb_helper.list_orders()
    confirmed = [o for o in orders if o.get("status") == "confirmed"]
    refunded = [o for o in orders if o.get("status") == "refunded"]

    total_orders = len(confirmed)
    total_refunds = len(refunded)

    total_revenue = sum(Decimal(str(o.get("total_amount", 0))) for o in confirmed)
    platform_fees = sum(Decimal(str(o.get("platform_fee", 0))) for o in confirmed)

    tickets_sold = sum(sum(int(i.get("quantity", 1)) for i in o.get("items", [])) for o in confirmed)

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
    admin: AttrDict = Depends(get_current_admin),
):
    orgs = dynamodb_helper.list_organizers()
    if status:
        orgs = [o for o in orgs if o.get("status") == status]

    start_idx = (page - 1) * limit
    page_orgs = orgs[start_idx : start_idx + limit]

    events = dynamodb_helper.list_events()
    orders = dynamodb_helper.list_orders()
    confirmed = [o for o in orders if o.get("status") == "confirmed"]

    result = []
    for org in page_orgs:
        org_id = org.get("OrganizerID") or org.get("id")
        org_event_ids = {e.get("EventID") or e.get("id") for e in events if e.get("organizer_id") == org_id}
        total_events = len(org_event_ids)
        rev = sum(Decimal(str(o.get("total_amount", 0))) for o in confirmed if o.get("event_id") in org_event_ids)

        result.append({
            "id": org_id,
            "email": org.get("email", ""),
            "full_name": org.get("full_name", ""),
            "business_name": org.get("business_name"),
            "status": org.get("status", "active"),
            "email_verified": org.get("email_verified", False),
            "total_events": total_events,
            "total_revenue": rev,
            "created_at": _format_dt(org.get("created_at")) or datetime.now(timezone.utc),
        })

    return result


@router.get("/organizers/{organizer_id}", response_model=OrganizerAdminResponse)
def get_organizer(
    organizer_id: str,
    admin: AttrDict = Depends(get_current_admin),
):
    org = dynamodb_helper.get_organizer(organizer_id)
    if not org:
        raise HTTPException(404, "Organizer not found")

    events = dynamodb_helper.list_events_by_organizer(organizer_id)
    total_events = len(events)
    return {
        "id": organizer_id,
        "email": org.get("email", ""),
        "full_name": org.get("full_name", ""),
        "business_name": org.get("business_name"),
        "status": org.get("status", "active"),
        "email_verified": org.get("email_verified", False),
        "total_events": total_events,
        "total_revenue": Decimal("0.00"),
        "created_at": _format_dt(org.get("created_at")) or datetime.now(timezone.utc),
    }


@router.put("/organizers/{organizer_id}/status")
def update_organizer_status(
    organizer_id: str,
    body: OrganizerStatusUpdate,
    admin: AttrDict = Depends(get_current_admin),
):
    org = dynamodb_helper.get_organizer(organizer_id)
    if not org:
        raise HTTPException(404, "Organizer not found")

    dynamodb_helper.update_organizer(organizer_id, {"status": body.status})
    dynamodb_helper.create_audit_log({
        "actor_type": "admin",
        "actor_id": admin.get("AdminID") or admin.get("id"),
        "actor_email": admin.get("email"),
        "action": f"organizer.status.{body.status}",
        "resource_type": "organizer",
        "resource_id": organizer_id,
        "meta": {"reason": body.reason},
    })
    return {"message": f"Organizer status updated to {body.status}"}


# ── Event Management ──────────────────────────────────────────────────────────

@router.get("/events")
def list_all_events(
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    admin: AttrDict = Depends(get_current_admin),
):
    events = dynamodb_helper.list_events()
    if status:
        events = [e for e in events if e.get("status") == status]
    events.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)

    formatted_events = []
    for e in events:
        evt_id = e.get("EventID") or e.get("id", "")
        org_id = e.get("organizer_id") or e.get("OrganizerID", "")
        org_name = e.get("organizer_name")
        if not org_name and org_id:
            org = dynamodb_helper.get_organizer(org_id)
            if org:
                org_name = org.get("business_name") or org.get("full_name") or "Organizer"
        
        formatted_events.append({
            **e,
            "id": evt_id,
            "EventID": evt_id,
            "organizer_name": org_name or "Official Organizer",
        })

    total = len(formatted_events)
    start_idx = (page - 1) * limit
    page_events = formatted_events[start_idx : start_idx + limit]

    return {"items": page_events, "total": total, "page": page, "limit": limit}


@router.put("/events/{event_id}/approve")
def approve_event(
    event_id: str,
    body: EventApproval,
    admin: AttrDict = Depends(get_current_admin),
):
    event = dynamodb_helper.get_event(event_id)
    if not event:
        raise HTTPException(404, f"Event '{event_id}' not found")

    admin_id = admin.get("AdminID") or admin.get("id")
    if body.approved:
        dynamodb_helper.update_event(event_id, {
            "status": "published",
            "approved_by": admin_id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "rejection_reason": None,
        })
    else:
        dynamodb_helper.update_event(event_id, {
            "status": "draft",
            "rejection_reason": body.rejection_reason,
        })

    dynamodb_helper.create_audit_log({
        "actor_type": "admin",
        "actor_id": admin_id,
        "actor_email": admin.get("email"),
        "action": "event.approved" if body.approved else "event.rejected",
        "resource_type": "event",
        "resource_id": event_id,
        "meta": {"reason": body.rejection_reason},
    })
    return {"message": "Event approved" if body.approved else "Event rejected"}


@router.put("/events/{event_id}/feature")
def feature_event(
    event_id: str,
    featured: bool,
    admin: AttrDict = Depends(get_current_admin),
):
    event = dynamodb_helper.get_event(event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    dynamodb_helper.update_event(event_id, {"is_featured": featured})
    return {"message": f"Event {'featured' if featured else 'unfeatured'}"}


@router.delete("/events/{event_id}")
def remove_event(
    event_id: str,
    admin: AttrDict = Depends(get_current_admin),
):
    event = dynamodb_helper.get_event(event_id)
    if not event:
        raise HTTPException(404, "Event not found")

    dynamodb_helper.create_audit_log({
        "actor_type": "admin",
        "actor_id": admin.get("AdminID") or admin.get("id"),
        "actor_email": admin.get("email"),
        "action": "event.removed",
        "resource_type": "event",
        "resource_id": event_id,
    })
    dynamodb_helper.delete_event(event_id)
    return {"message": "Event removed"}


# ── Event Categories ──────────────────────────────────────────────────────────

@router.post("/categories", response_model=EventCategoryResponse, status_code=201)
def create_category(
    body: EventCategoryCreate,
    admin: AttrDict = Depends(get_current_admin),
):
    import re
    cat_id = str(uuid.uuid4())
    slug = body.slug
    if not slug:
        slug = re.sub(r'[^a-z0-9]+', '-', body.name.lower()).strip('-')
    if not slug:
        slug = f"cat-{cat_id[:8]}"

    existing = dynamodb_helper.get_category_by_slug(slug)
    if existing:
        slug = f"{slug}-{cat_id[:4]}"

    data_to_save = body.model_dump()
    data_to_save["slug"] = slug

    data = dynamodb_helper.create_category(cat_id, data_to_save)
    return EventCategoryResponse(
        id=cat_id,
        name=data.get("name", ""),
        slug=data.get("slug", ""),
        icon=data.get("icon"),
        color=data.get("color"),
    )


@router.put("/categories/{category_id}", response_model=EventCategoryResponse)
def update_category(
    category_id: str,
    body: EventCategoryCreate,
    admin: AttrDict = Depends(get_current_admin),
):
    cat = dynamodb_helper.get_category(category_id)
    if not cat:
        raise HTTPException(404, "Category not found")

    data = body.model_dump()
    data["CategoryID"] = category_id
    updated = dynamodb_helper.create_category(category_id, data)

    return EventCategoryResponse(
        id=category_id,
        name=updated.get("name", ""),
        slug=updated.get("slug", ""),
        icon=updated.get("icon"),
        sort_order=int(updated.get("sort_order", 0)),
    )


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: str,
    admin: AttrDict = Depends(get_current_admin),
):
    cat = dynamodb_helper.get_category(category_id)
    if not cat:
        raise HTTPException(404, "Category not found")
    dynamodb_helper.delete_category(category_id)
    return {"message": "Category deleted"}


# ── Financial ─────────────────────────────────────────────────────────────────

@router.get("/orders")
def all_orders(
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200),
    admin: AttrDict = Depends(get_current_admin),
):
    orders = dynamodb_helper.list_orders()
    orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    total = len(orders)
    start_idx = (page - 1) * limit
    page_orders = orders[start_idx : start_idx + limit]
    return {"items": page_orders, "total": total}


@router.post("/payouts", response_model=PayoutResponse, status_code=201)
def create_payout(
    body: PayoutRequest,
    admin: AttrDict = Depends(get_current_admin),
):
    org = dynamodb_helper.get_organizer(body.organizer_id)
    if not org:
        raise HTTPException(404, "Organizer not found")

    payout_id = str(uuid.uuid4())
    payout_data = dynamodb_helper.create_payout(payout_id, {
        "organizer_id": body.organizer_id,
        "amount": str(body.amount),
        "notes": body.notes,
        "status": "pending",
    })

    return PayoutResponse(
        id=payout_id,
        organizer_id=body.organizer_id,
        amount=body.amount,
        currency="GHS",
        status="pending",
        notes=body.notes,
        created_at=datetime.now(timezone.utc),
        processed_at=None,
    )


@router.put("/payouts/{payout_id}/process")
def process_payout(
    payout_id: str,
    admin: AttrDict = Depends(get_current_admin),
):
    payout = dynamodb_helper.get_payout(payout_id)
    if not payout:
        raise HTTPException(404, "Payout not found")

    dynamodb_helper.update_payout(payout_id, {
        "status": "processed",
        "processed_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"message": "Payout processed"}


# ── Platform Config ───────────────────────────────────────────────────────────

@router.get("/config/commission")
def get_commission(
    admin: AttrDict = Depends(get_current_admin),
):
    setting = dynamodb_helper.get_platform_setting("commission_percent")
    val = 5.0
    if setting and isinstance(setting, dict):
        raw_val = setting.get("value") or setting.get("val") or "5.0"
        try:
            val = float(str(raw_val))
        except (ValueError, TypeError):
            val = 5.0
    elif isinstance(setting, (int, float, str)):
        try:
            val = float(str(setting))
        except (ValueError, TypeError):
            val = 5.0
    return {"commission_percent": val}


@router.put("/config/commission")
def update_commission(
    body: CommissionUpdate,
    admin: AttrDict = Depends(get_current_admin),
):
    dynamodb_helper.set_platform_setting("commission_percent", str(body.commission_percent))
    dynamodb_helper.create_audit_log({
        "actor_type": "admin",
        "actor_id": admin.get("AdminID") or admin.get("id"),
        "actor_email": admin.get("email"),
        "action": "config.commission.updated",
        "meta": {"new_value": body.commission_percent},
    })
    return {"message": f"Commission updated to {body.commission_percent}%"}



# ── Audit Logs ────────────────────────────────────────────────────────────────

@router.get("/audit-logs", response_model=list[AuditLogResponse])
def audit_logs(
    page: int = Query(1, ge=1), limit: int = Query(100, ge=1, le=500),
    admin: AttrDict = Depends(get_current_admin),
):
    logs = dynamodb_helper.list_audit_logs()
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    start_idx = (page - 1) * limit
    page_logs = logs[start_idx : start_idx + limit]

    return [
        AuditLogResponse(
            id=l.get("LogID") or l.get("id", ""),
            actor_type=l.get("actor_type", ""),
            actor_id=l.get("actor_id"),
            actor_email=l.get("actor_email"),
            action=l.get("action", ""),
            resource_type=l.get("resource_type"),
            resource_id=l.get("resource_id"),
            ip_address=l.get("ip_address"),
            user_agent=l.get("user_agent"),
            meta=l.get("meta"),
            created_at=_format_dt(l.get("timestamp")) or datetime.now(timezone.utc),
        )
        for l in page_logs
    ]


# ── Admin Management ──────────────────────────────────────────────────────────

@router.get("/admins", response_model=list[AdminResponse])
def list_admins(admin: AttrDict = Depends(get_super_admin)):
    admins = dynamodb_helper.list_admins()
    return [
        AdminResponse(
            id=a.get("AdminID") or a.get("id", ""),
            email=a.get("email", ""),
            full_name=a.get("full_name", ""),
            is_active=a.get("is_active", True),
            is_super=a.get("is_super", False),
            email_verified=a.get("email_verified", True),
            created_at=_format_dt(a.get("created_at")) or datetime.now(timezone.utc),
        )
        for a in admins
    ]


@router.put("/admins/{admin_id}/deactivate")
def deactivate_admin(
    admin_id: str,
    admin: AttrDict = Depends(get_super_admin),
):
    current_id = admin.get("AdminID") or admin.get("id")
    if admin_id == current_id:
        raise HTTPException(400, "Cannot deactivate yourself")

    target = dynamodb_helper.get_admin(admin_id)
    if not target:
        raise HTTPException(404, "Admin not found")

    dynamodb_helper.update_admin(admin_id, {"is_active": False})
    return {"message": "Admin deactivated"}


# ── Config Management ─────────────────────────────────────────────────────────

@router.get("/config")
def list_configs(admin: AttrDict = Depends(get_current_admin)):
    return dynamodb_helper.list_platform_settings()


@router.put("/config/{key}")
def update_config_value(
    key: str,
    value: str,
    admin: AttrDict = Depends(get_super_admin),
):
    dynamodb_helper.set_platform_setting(key, value)
    dynamodb_helper.create_audit_log({
        "actor_type": "admin",
        "actor_id": admin.get("AdminID") or admin.get("id"),
        "actor_email": admin.get("email"),
        "action": f"config.{key}.updated",
        "meta": {"value": value},
    })
    return {"message": f"Config {key} updated to: {value}"}


# ── Create Admin Account ──────────────────────────────────────────────────────

@router.post("/create-admin", response_model=AdminResponse, status_code=201)
def create_new_admin(
    body: AdminCreate,
    admin: AttrDict = Depends(get_super_admin),
):
    if dynamodb_helper.get_admin_by_email(body.email):
        raise HTTPException(400, "Email already registered")

    admin_id = str(uuid.uuid4())
    admin_data = dynamodb_helper.create_admin(admin_id, {
        "email": body.email,
        "full_name": body.full_name,
        "password_hash": hash_password(body.password),
        "is_super": body.is_super,
        "is_active": True,
        "email_verified": True,
    })

    dynamodb_helper.create_audit_log({
        "actor_type": "admin",
        "actor_id": admin.get("AdminID") or admin.get("id"),
        "actor_email": admin.get("email"),
        "action": "admin.created",
        "resource_type": "admin",
        "resource_id": admin_id,
    })

    return AdminResponse(
        id=admin_id,
        email=admin_data["email"],
        full_name=admin_data["full_name"],
        is_active=True,
        is_super=body.is_super,
        email_verified=True,
        created_at=datetime.now(timezone.utc),
    )


# ── Resale Monitoring & Approvals ─────────────────────────────────────────────

@router.get("/resale")
def list_resale_listings(
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    admin: AttrDict = Depends(get_current_admin),
):
    listings = dynamodb_helper.list_resale_listings_by_status(status) if status else dynamodb_helper._scan_all(dynamodb_helper.resale_listings_table_name)
    total = len(listings)
    start_idx = (page - 1) * limit
    page_l = listings[start_idx : start_idx + limit]
    return {"items": page_l, "total": total}


@router.put("/resale/{listing_id}/approve")
def approve_resale_listing(
    listing_id: str,
    body: ResaleApproval,
    admin: AttrDict = Depends(get_current_admin),
):
    listing = dynamodb_helper.get_resale_listing(listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    if listing.get("status") != "pending":
        raise HTTPException(400, f"Listing is not in pending state (status: {listing.get('status')})")

    ticket_id = listing.get("ticket_id")
    if body.approved:
        dynamodb_helper.update_resale_listing(listing_id, {"status": "active"})
    else:
        dynamodb_helper.update_resale_listing(listing_id, {"status": "removed"})
        if ticket_id:
            dynamodb_helper.update_ticket(ticket_id, {"status": "active"})

    dynamodb_helper.create_audit_log({
        "actor_type": "admin",
        "actor_id": admin.get("AdminID") or admin.get("id"),
        "actor_email": admin.get("email"),
        "action": "resale.approved" if body.approved else "resale.rejected",
        "resource_type": "resale_listing",
        "resource_id": listing_id,
    })
    return {"message": "Resale listing approved" if body.approved else "Resale listing rejected"}


# ── Refund Management ─────────────────────────────────────────────────────────

@router.get("/refunds")
def list_pending_refund_requests(
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200),
    admin: AttrDict = Depends(get_current_admin),
):
    orders = dynamodb_helper.list_orders()
    pending = [o for o in orders if o.get("status") == "refund_pending"]
    total = len(pending)
    start_idx = (page - 1) * limit
    page_orders = pending[start_idx : start_idx + limit]
    return {"items": page_orders, "total": total}


@router.put("/orders/{order_id}/refund")
def process_order_refund(
    order_id: str,
    body: RefundApproval,
    admin: AttrDict = Depends(get_current_admin),
):
    order = dynamodb_helper.get_order(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if order.get("status") not in ("confirmed", "refund_pending"):
        raise HTTPException(400, f"Order cannot be refunded (status: {order.get('status')})")

    if body.approved:
        dynamodb_helper.update_order(order_id, {"status": "refunded"})
        tickets = order.get("tickets", [])
        for t in tickets:
            t_id = t.get("TicketID") or t.get("id")
            if t_id:
                dynamodb_helper.update_ticket(t_id, {"status": "cancelled"})
        message = "Refund approved and processed successfully"
    else:
        dynamodb_helper.update_order(order_id, {"status": "confirmed"})
        message = f"Refund request rejected. Reason: {body.rejection_reason or 'None'}"

    dynamodb_helper.create_audit_log({
        "actor_type": "admin",
        "actor_id": admin.get("AdminID") or admin.get("id"),
        "actor_email": admin.get("email"),
        "action": "order.refund_approved" if body.approved else "order.refund_rejected",
        "resource_type": "order",
        "resource_id": order_id,
        "meta": {"reason": body.rejection_reason},
    })
    return {"message": message}


# ── Admin Analytics ───────────────────────────────────────────────────────────

@router.get("/analytics")
def platform_analytics(admin: AttrDict = Depends(get_current_admin)):
    orgs = dynamodb_helper.list_organizers()
    orders = dynamodb_helper.list_orders()
    confirmed = [o for o in orders if o.get("status") == "confirmed"]

    org_months: Dict[str, int] = {}
    for o in orgs:
        created = o.get("created_at", "")[:7]
        if created:
            org_months[created] = org_months.get(created, 0) + 1

    sales_months: Dict[str, Dict[str, Any]] = {}
    for o in confirmed:
        created = o.get("created_at", "")[:7]
        if created:
            if created not in sales_months:
                sales_months[created] = {"orders": 0, "revenue": 0.0}
            sales_months[created]["orders"] += 1
            sales_months[created]["revenue"] += float(o.get("total_amount", 0))

    listings = dynamodb_helper._scan_all(dynamodb_helper.resale_listings_table_name)
    total_listed = len(listings)
    sold_listings = [l for l in listings if l.get("status") == "sold"]
    resale_revenue = sum(float(l.get("asking_price", 0)) for l in sold_listings)

    return {
        "organizer_growth": [{"month": m, "count": c} for m, c in sorted(org_months.items())],
        "sales_growth": [{"month": m, "orders": data["orders"], "revenue": data["revenue"]} for m, data in sorted(sales_months.items())],
        "top_events": [],
        "resale_activity": {
            "total_listed": total_listed,
            "total_sold": len(sold_listings),
            "resale_revenue": resale_revenue,
        }
    }
