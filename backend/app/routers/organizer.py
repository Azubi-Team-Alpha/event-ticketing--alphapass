"""Organizer dashboard and analytics routes using DynamoDB."""
import io
import csv
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
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
    format: str = Query("json"),
    org: AttrDict = Depends(get_current_organizer),
):
    org_id = org.get("OrganizerID") or org.get("id")
    event = dynamodb_helper.get_event(event_id)
    if not event or event.get("organizer_id") != org_id:
        raise HTTPException(404, "Event not found")

    orders = dynamodb_helper.list_orders_by_event(event_id)
    confirmed_orders = [o for o in orders if o.get("status") == "confirmed"]

    tickets = []
    for o in confirmed_orders:
        tickets.extend(o.get("tickets", []))

    if format.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Ticket Code", "Attendee Name", "Attendee Email", "Ticket Type", "Status", "Checked In", "Checked In At"])
        for t in tickets:
            writer.writerow([
                t.get("ticket_code"),
                t.get("attendee_name"),
                t.get("attendee_email"),
                t.get("ticket_type_name", ""),
                t.get("status", "active"),
                "Yes" if t.get("is_used") else "No",
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
            "attendee_name": t.get("attendee_name"),
            "attendee_email": t.get("attendee_email"),
            "ticket_type": t.get("ticket_type_name"),
            "status": t.get("status", "active"),
            "checked_in": t.get("is_used", False),
            "checked_in_at": t.get("used_at"),
        }
        for t in tickets
    ]


@router.get("/payouts", response_model=list[PayoutResponse])
def my_payouts(org: AttrDict = Depends(get_current_organizer)):
    org_id = org.get("OrganizerID") or org.get("id")
    payouts = dynamodb_helper.list_payouts_by_organizer(org_id)
    return [
        PayoutResponse(
            id=p.get("PayoutID") or p.get("id", ""),
            organizer_id=org_id,
            amount=Decimal(str(p.get("amount", 0))),
            status=p.get("status", "pending"),
            notes=p.get("notes"),
            requested_at=_format_dt(p.get("created_at")) or datetime.now(timezone.utc),
            processed_at=_format_dt(p.get("processed_at")),
        )
        for p in payouts
    ]
