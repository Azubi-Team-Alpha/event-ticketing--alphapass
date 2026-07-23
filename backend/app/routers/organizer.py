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
from app.routers.orders import _format_order_response

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


@router.get("/dashboard", response_model=OrganizerDashboard)
def organizer_dashboard(org: AttrDict = Depends(get_current_organizer)):
    org_id = org.get("OrganizerID") or org.get("id")
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

    return {
        "total_events": total_events,
        "published_events": published_events,
        "total_orders": total_orders,
        "total_tickets_sold": total_tickets_sold,
        "gross_revenue": gross_revenue,
        "platform_fees": platform_fees,
        "net_earnings": net_earnings,
        "pending_payout": pending_payout,
        "total_transfers": 0,
        "total_resale_listings": 0,
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
    
    attendance_rate = 0.0

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
        "attendance_rate": round(attendance_rate, 2),
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
    except Exception:
        raise HTTPException(401, "Invalid or expired authentication token")

    event = dynamodb_helper.get_event(event_id)
    if not event or (event.get("organizer_id") != org_id and event.get("OrganizerID") != org_id):
        raise HTTPException(404, "Event not found")

    orders = dynamodb_helper.list_orders_by_event(event_id)
    confirmed_orders = [o for o in orders if o.get("status") in ("confirmed", "paid", "completed")]

    tickets = []
    for o in confirmed_orders:
        o_tickets = o.get("tickets") or []
        for t in o_tickets:
            tickets.append({
                **t,
                "guest_name": o.get("guest_name"),
                "guest_email": o.get("guest_email")
            })

    is_csv = (export and export.lower() == "csv") or (format and format.lower() == "csv")
    if is_csv:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Ticket Code", "Attendee Name", "Attendee Email", "Ticket Type", "Status", "Checked In", "Checked In At"])
        for t in tickets:
            writer.writerow([
                t.get("ticket_code"),
                t.get("attendee_name") or t.get("guest_name") or "Guest",
                t.get("attendee_email") or t.get("guest_email") or "",
                t.get("ticket_type_name", "Pass"),
                t.get("status", "active"),
                "Yes" if (t.get("is_used") or t.get("checked_in")) else "No",
                t.get("used_at", "")
            ])
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=attendees_event_{event_id}.csv"}
        )

    return [
        {
            "ticket_code": t.get("ticket_code"),
            "attendee_name": t.get("attendee_name") or t.get("guest_name") or "Guest",
            "attendee_email": t.get("attendee_email") or t.get("guest_email") or "",
            "ticket_type": t.get("ticket_type_name", "Pass"),
            "status": t.get("status", "active"),
            "is_used": t.get("is_used", False) or t.get("checked_in", False),
            "checked_in": t.get("is_used", False) or t.get("checked_in", False),
            "checked_in_at": t.get("used_at"),
        }
        for t in tickets
    ]


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

