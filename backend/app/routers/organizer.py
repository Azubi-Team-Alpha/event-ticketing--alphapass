"""Organizer dashboard and analytics routes."""
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.base import get_db
from app.models.models import (
    Event, EventStatus, Order, OrderItem, Ticket, TicketTransfer,
    ResaleListing, OrganizerPayout, PayoutStatus, Organizer,
    OrderStatus, TicketStatus,
)
from app.schemas.schemas import (
    OrganizerDashboard, EventAnalytics, OrderResponse, PayoutResponse,
)
from app.core.dependencies import get_current_organizer, get_active_organizer

router = APIRouter()


@router.get("/dashboard", response_model=OrganizerDashboard)
def organizer_dashboard(
    db: Session = Depends(get_db),
    org: Organizer = Depends(get_current_organizer),
):
    event_ids = [e.id for e in db.query(Event.id).filter(Event.organizer_id == org.id).all()]

    total_events = len(event_ids)
    published_events = db.query(Event).filter(
        Event.organizer_id == org.id, Event.status == EventStatus.published
    ).count()

    orders = db.query(Order).filter(
        Order.event_id.in_(event_ids), Order.status == OrderStatus.confirmed
    ).all() if event_ids else []

    total_orders = len(orders)
    total_tickets_sold = sum(o.total_tickets for o in orders)
    gross_revenue = sum(o.total_amount for o in orders) if orders else Decimal("0.00")
    platform_fees = sum(o.platform_fee for o in orders) if orders else Decimal("0.00")
    net_earnings = gross_revenue - platform_fees

    processed_payouts = db.query(func.sum(OrganizerPayout.amount)).filter(
        OrganizerPayout.organizer_id == org.id,
        OrganizerPayout.status == PayoutStatus.processed,
    ).scalar() or Decimal("0.00")
    pending_payout = net_earnings - processed_payouts

    transfer_count = db.query(TicketTransfer).join(Ticket).join(
        __import__('app.models.models', fromlist=['OrderItem']).OrderItem
    ).filter(
        TicketTransfer.is_completed == True
    ).count() if event_ids else 0

    resale_count = db.query(ResaleListing).count() if event_ids else 0

    return {
        "total_events": total_events, "published_events": published_events,
        "total_orders": total_orders, "total_tickets_sold": total_tickets_sold,
        "gross_revenue": gross_revenue, "platform_fees": platform_fees,
        "net_earnings": net_earnings, "pending_payout": pending_payout,
        "total_transfers": transfer_count, "total_resale_listings": resale_count,
    }


@router.get("/events/{event_id}/analytics", response_model=EventAnalytics)
def event_analytics(
    event_id: str, db: Session = Depends(get_db),
    org: Organizer = Depends(get_current_organizer),
):
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == org.id).first()
    if not event:
        raise HTTPException(404, "Event not found")

    orders = db.query(Order).filter(
        Order.event_id == event_id, Order.status == OrderStatus.confirmed
    ).all()

    gross = sum(o.total_amount for o in orders) if orders else Decimal("0.00")
    refund_count = db.query(Order).filter(
        Order.event_id == event_id, Order.status == OrderStatus.refunded
    ).count()

    transfer_count = 0
    resale_count = 0
    tickets_used = 0

    total_cap = event.total_capacity
    total_sold = event.total_sold
    attendance_rate = (tickets_used / total_sold * 100) if total_sold > 0 else 0.0

    breakdown = []
    for tt in event.ticket_types:
        breakdown.append({
            "id": tt.id, "name": tt.name, "price": str(tt.price),
            "quantity": tt.quantity, "sold": tt.quantity_sold,
            "revenue": str(tt.price * tt.quantity_sold),
        })

    return {
        "event_id": event_id, "event_title": event.title,
        "total_capacity": total_cap, "total_sold": total_sold,
        "attendance_rate": round(attendance_rate, 2),
        "gross_revenue": gross, "refund_count": refund_count,
        "transfer_count": transfer_count, "resale_count": resale_count,
        "ticket_type_breakdown": breakdown,
    }


@router.get("/events/{event_id}/orders", response_model=list[OrderResponse])
def event_orders(
    event_id: str,
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    org: Organizer = Depends(get_current_organizer),
):
    if not db.query(Event).filter(Event.id == event_id, Event.organizer_id == org.id).first():
        raise HTTPException(404, "Event not found")
    orders = db.query(Order).filter(Order.event_id == event_id).offset((page - 1) * limit).limit(limit).all()
    return orders


@router.get("/events/{event_id}/attendees")
def export_attendees(
    event_id: str,
    format: str = Query("json"),
    db: Session = Depends(get_db),
    org: Organizer = Depends(get_current_organizer),
):
    if not db.query(Event).filter(Event.id == event_id, Event.organizer_id == org.id).first():
        raise HTTPException(404, "Event not found")
    tickets = (
        db.query(Ticket)
        .join(OrderItem)
        .join(Order)
        .filter(Order.event_id == event_id, Order.status == OrderStatus.confirmed)
        .all()
    )

    if format.lower() == "csv":
        import io
        import csv
        from fastapi.responses import StreamingResponse
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Ticket Code", "Attendee Name", "Attendee Email", "Ticket Type", "Status", "Checked In", "Checked In At"])
        for t in tickets:
            writer.writerow([
                t.ticket_code,
                t.attendee_name,
                t.attendee_email,
                t.ticket_type.name if t.ticket_type else "",
                t.status.value if hasattr(t.status, "value") else t.status,
                "Yes" if t.is_used else "No",
                t.used_at.isoformat() if t.used_at else ""
            ])
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=attendees_event_{event_id}.csv"}
        )

    return [
        {
            "ticket_code": t.ticket_code,
            "attendee_name": t.attendee_name,
            "attendee_email": t.attendee_email,
            "ticket_type": t.ticket_type.name if t.ticket_type else None,
            "status": t.status.value if hasattr(t.status, 'value') else t.status,
            "checked_in": t.is_used,
            "checked_in_at": t.used_at,
        }
        for t in tickets
    ]


@router.get("/payouts", response_model=list[PayoutResponse])
def my_payouts(
    db: Session = Depends(get_db),
    org: Organizer = Depends(get_current_organizer),
):
    return db.query(OrganizerPayout).filter(OrganizerPayout.organizer_id == org.id).all()
