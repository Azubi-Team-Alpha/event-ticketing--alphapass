"""Organizer dashboard and analytics routes using DynamoDB."""
import io
import csv
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.db.dynamodb import dynamodb_helper
from app.schemas.schemas import (
    OrganizerDashboard, EventAnalytics, OrderResponse, PayoutResponse,
)
from app.core.dependencies import get_current_organizer, AttrDict
from app.core.utils import format_dt as _format_dt
from app.routers.orders import _format_order_response

router = APIRouter()





@router.get("/dashboard", response_model=OrganizerDashboard)
def organizer_dashboard(org: AttrDict = Depends(get_current_organizer)):
    org_id = str(org.get("OrganizerID") or org.get("id") or "")
    events = dynamodb_helper.list_events_by_organizer(org_id)
    
    total_events = len(events)
    published_events = sum(1 for e in events if e.get("status") == "published")
    event_ids = {e.get("EventID") or e.get("id") for e in events}

    orders = []
    for eid in event_ids:
        if eid:
            e_orders = dynamodb_helper.list_orders_by_event(eid)
            orders.extend([o for o in e_orders if o.get("status") == "confirmed"])

    total_orders = len(orders)
    total_tickets_sold = sum(sum(int(i.get("quantity", 1)) for i in o.get("items", [])) for o in orders)
    gross_revenue = sum(Decimal(str(o.get("total_amount", 0))) for o in orders)
    platform_fees = sum(Decimal(str(o.get("platform_fee", 0))) for o in orders)
    net_earnings = gross_revenue - platform_fees

    payouts = dynamodb_helper.list_payouts_by_organizer(org_id)
    processed_payouts = sum(Decimal(str(p.get("amount", 0))) for p in payouts if p.get("status") == "processed")
    pending_payout = max(Decimal("0.00"), net_earnings - processed_payouts)

    # Wire real transfer and resale counts across all organizer events
    total_transfers = 0
    total_resale_listings = 0
    for eid in event_ids:
        if eid:
            try:
                transfers = dynamodb_helper.list_transfers_by_event(eid) if hasattr(dynamodb_helper, "list_transfers_by_event") else []
                total_transfers += len(transfers)
            except Exception:
                pass
            try:
                listings = dynamodb_helper.list_resale_listings_by_event(eid) if hasattr(dynamodb_helper, "list_resale_listings_by_event") else []
                total_resale_listings += len(listings)
            except Exception:
                pass

    return {
        "total_events": total_events,
        "published_events": published_events,
        "total_orders": total_orders,
        "total_tickets_sold": total_tickets_sold,
        "gross_revenue": gross_revenue,
        "platform_fees": platform_fees,
        "net_earnings": net_earnings,
        "pending_payout": pending_payout,
        "total_transfers": total_transfers,
        "total_resale_listings": total_resale_listings,
    }


@router.get("/events/{event_id}/analytics", response_model=EventAnalytics)
def event_analytics(
    event_id: str,
    org: AttrDict = Depends(get_current_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    event = dynamodb_helper.get_event(event_id)
    if not event or event.get("organizer_id") != org_id:
        raise HTTPException(404, "Event not found")

    orders = dynamodb_helper.list_orders_by_event(event_id)
    confirmed = [o for o in orders if o.get("status") == "confirmed"]
    refunded = [o for o in orders if o.get("status") == "refunded"]

    gross = sum(Decimal(str(o.get("total_amount", 0))) for o in confirmed)
    refund_count = len(refunded)

    ticket_types = event.get("ticket_types", [])
    total_cap = sum(int(tt.get("quantity", 0)) for tt in ticket_types)
    total_sold = sum(int(tt.get("quantity_sold", 0)) for tt in ticket_types)
    
    attendance_rate = round((total_sold / total_cap * 100), 2) if total_cap > 0 else 0.0

    breakdown = []
    for tt in ticket_types:
        price = Decimal(str(tt.get("price", 0)))
        sold = int(tt.get("quantity_sold", 0))
        breakdown.append({
            "id": tt.get("id", ""),
            "name": tt.get("name", ""),
            "price": str(price),
            "quantity": int(tt.get("quantity", 0)),
            "sold": sold,
            "revenue": str(price * sold),
        })

    return {
        "event_id": event_id,
        "event_title": event.get("title", ""),
        "total_capacity": total_cap,
        "total_sold": total_sold,
        "attendance_rate": attendance_rate,
        "gross_revenue": gross,
        "refund_count": refund_count,
        "transfer_count": 0,
        "resale_count": 0,
        "ticket_type_breakdown": breakdown,
    }


@router.get("/events/{event_id}/orders", response_model=list[OrderResponse])
def event_orders(
    event_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    org: AttrDict = Depends(get_current_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    event = dynamodb_helper.get_event(event_id)
    if not event or event.get("organizer_id") != org_id:
        raise HTTPException(404, "Event not found")

    orders = dynamodb_helper.list_orders_by_event(event_id)
    start_idx = (page - 1) * limit
    page_orders = orders[start_idx : start_idx + limit]
    return [_format_order_response(o) for o in page_orders]


@router.get("/events/{event_id}/attendees")
def export_attendees(
    event_id: str,
    request: Request,
    format: str = Query("json"),
    export: str | None = Query(None),
    token: str | None = Query(None),
):
    from app.core.security import decode_access_token
    auth_header = request.headers.get("Authorization") if request else None
    jwt_token = token
    if not jwt_token and auth_header and auth_header.startswith("Bearer "):
        jwt_token = auth_header.split(" ")[1]

    if not jwt_token:
        raise HTTPException(401, "Authentication token required")

    try:
        payload = decode_access_token(jwt_token)
        org_id = payload.get("sub")
        role = payload.get("role")
    except Exception:
        raise HTTPException(401, "Invalid or expired authentication token")

    event = dynamodb_helper.get_event(event_id)
    if not event:
        raise HTTPException(404, "Event not found")

    if role != "admin":
        e_org = str(event.get("organizer_id") or event.get("OrganizerID") or "").lower()
        if e_org and e_org != str(org_id).lower():
            raise HTTPException(404, "Event not found")

    orders = dynamodb_helper.list_orders_by_event(event_id)
    valid_orders = [o for o in orders if str(o.get("status", "confirmed")).lower() not in ("cancelled", "refunded", "failed")]

    tickets = []
    for o in valid_orders:
        o_id = str(o.get("OrderID") or o.get("id") or "")
        o_tickets = o.get("tickets") or []
        if not o_tickets and o_id:
            o_tickets = dynamodb_helper.list_tickets_by_order(o_id)

        if o_tickets:
            for t in o_tickets:
                tickets.append({
                    "ticket_code": t.get("ticket_code") or t.get("code") or "PASS",
                    "attendee_name": t.get("attendee_name") or o.get("guest_name") or "Guest",
                    "attendee_email": t.get("attendee_email") or o.get("guest_email") or "",
                    "ticket_type": t.get("ticket_type_name") or "Pass",
                    "status": t.get("status", "active"),
                    "is_used": bool(t.get("is_used") or t.get("checked_in")),
                    "checked_in": bool(t.get("is_used") or t.get("checked_in")),
                    "checked_in_at": t.get("used_at"),
                })
        else:
            items = o.get("items") or []
            if not items:
                items = [{"quantity": 1, "ticket_type_name": "General Admission"}]
            for idx, item in enumerate(items):
                qty = int(item.get("quantity", 1))
                for q_idx in range(qty):
                    t_code = f"AP-{o_id[:6].upper() if o_id else '8821'}-{idx+1}-{q_idx+1}"
                    tickets.append({
                        "ticket_code": t_code,
                        "attendee_name": o.get("guest_name") or "Guest",
                        "attendee_email": o.get("guest_email") or "",
                        "ticket_type": item.get("ticket_type_name") or "Pass",
                        "status": o.get("status", "active"),
                        "is_used": False,
                        "checked_in": False,
                        "checked_in_at": None,
                    })

    is_csv = (export and export.lower() == "csv") or (format and format.lower() == "csv")
    if is_csv:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Ticket Code", "Attendee Name", "Attendee Email", "Ticket Type", "Status", "Checked In", "Checked In At"])
        for t in tickets:
            writer.writerow([
                t.get("ticket_code"),
                t.get("attendee_name"),
                t.get("attendee_email"),
                t.get("ticket_type"),
                t.get("status"),
                "Yes" if t.get("checked_in") else "No",
                t.get("checked_in_at") or "",
            ])
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=attendees_event_{event_id}.csv"}
        )

    return tickets


@router.get("/payouts", response_model=list[PayoutResponse])
def my_payouts(org: AttrDict = Depends(get_current_organizer)):
    org_id = str(org.get("OrganizerID") or org.get("id") or "")
    payouts = dynamodb_helper.list_payouts_by_organizer(org_id)
    return [
        PayoutResponse(
            id=p.get("PayoutID") or p.get("id", ""),
            organizer_id=org_id,
            amount=Decimal(str(p.get("amount", 0))),
            currency="GHS",
            status=p.get("status", "pending"),
            notes=p.get("notes"),
            created_at=_format_dt(p.get("created_at")) or datetime.now(timezone.utc),
            processed_at=_format_dt(p.get("processed_at")),
        )
        for p in payouts
    ]


@router.post("/payouts", response_model=PayoutResponse, status_code=201)
def request_payout(
    body: Dict[str, Any],
    org: AttrDict = Depends(get_current_organizer),
):
    import uuid
    org_id = str(org.get("OrganizerID") or org.get("id") or "")
    amount = float(body.get("amount", 0))
    if amount <= 0:
        raise HTTPException(400, "Payout amount must be greater than 0")

    payout_id = str(uuid.uuid4())
    notes = f"Bank/MoMo: {body.get('bank', 'MTN MoMo')}, Account: {body.get('account_number', '')}"
    payout_data = dynamodb_helper.create_payout(payout_id, {
        "organizer_id": org_id,
        "amount": amount,
        "status": "pending",
        "notes": notes,
    })

    return PayoutResponse(
        id=payout_id,
        organizer_id=org_id,
        amount=Decimal(str(amount)),
        currency="GHS",
        status="pending",
        notes=notes,
        created_at=datetime.now(timezone.utc),
    )

