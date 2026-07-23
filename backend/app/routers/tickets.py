"""Ticket lookup routes using DynamoDB."""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Response

from app.db.dynamodb import dynamodb_helper
from app.schemas.schemas import TicketResponse
from app.core.dependencies import get_current_user, AttrDict

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


def _format_ticket_response(ticket: Dict[str, Any]) -> TicketResponse:
    t_id = ticket.get("TicketID") or ticket.get("id", "")
    t_code = ticket.get("ticket_code", "")
    qr_url = ticket.get("qr_image_url") or f"/tickets/{t_code}/qr"
    return TicketResponse(
        id=t_id,
        order_item_id=ticket.get("order_item_id", ""),
        ticket_code=t_code,
        qr_image_url=qr_url,
        status=ticket.get("status", "active"),
        is_used=ticket.get("is_used", False),
        used_at=_format_dt(ticket.get("used_at")),
        attendee_name=ticket.get("attendee_name"),
        attendee_email=ticket.get("attendee_email"),
        issued_at=_format_dt(ticket.get("issued_at")) or datetime.now(timezone.utc),
    )


@router.get("/{ticket_code}", response_model=TicketResponse)
def get_ticket(ticket_code: str):
    """Public ticket lookup by code (for guest re-download)."""
    ticket = dynamodb_helper.get_ticket_by_code(ticket_code)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return _format_ticket_response(ticket)


@router.get("/{ticket_code}/qr")
def get_ticket_qr(ticket_code: str):
    """Generate and return raw PNG QR code bytes for a ticket code."""
    from app.core.qr import generate_qr_code
    qr_bytes = generate_qr_code(ticket_code)
    return Response(content=qr_bytes, media_type="image/png")


@router.get("/{ticket_code}/status")
def ticket_status(ticket_code: str):
    ticket = dynamodb_helper.get_ticket_by_code(ticket_code)
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    event = None
    event_id = ticket.get("event_id")
    if not event_id and ticket.get("order_id"):
        order = dynamodb_helper.get_order(ticket["order_id"])
        if order:
            event_id = order.get("event_id")

    if event_id:
        event = dynamodb_helper.get_event(event_id)

    return {
        "ticket_code": ticket.get("ticket_code"),
        "status": ticket.get("status", "active"),
        "is_used": ticket.get("is_used", False),
        "used_at": ticket.get("used_at"),
        "attendee_name": ticket.get("attendee_name"),
        "ticket_type": ticket.get("ticket_type_name"),
        "event_title": event.get("title") if event else None,
        "event_starts_at": event.get("starts_at") if event else None,
        "qr_image_url": ticket.get("qr_image_url") or f"/tickets/{ticket_code}/qr",
    }


@router.get("/{ticket_code}/pdf")
def download_ticket_pdf(ticket_code: str):
    """Generate and download official PDF ticket with full event metadata."""
    from app.core.pdf import generate_ticket_pdf

    ticket = dynamodb_helper.get_ticket_by_code(ticket_code)
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    event = None
    event_id = ticket.get("event_id")
    if not event_id and ticket.get("order_id"):
        order = dynamodb_helper.get_order(ticket["order_id"])
        if order:
            event_id = order.get("event_id")

    if event_id:
        event = dynamodb_helper.get_event(event_id)

    class DummyTicket:
        def __init__(self, d, evt):
            self.id = d.get("TicketID") or d.get("id")
            self.ticket_code = d.get("ticket_code")
            self.attendee_name = d.get("attendee_name") or "Guest Attendee"
            self.attendee_email = d.get("attendee_email")
            self.qr_image_url = d.get("qr_image_url") or f"/tickets/{d.get('ticket_code')}/qr"
            self.ticket_type_name = d.get("ticket_type_name") or "General Pass"
            self.event = evt

    t_obj = DummyTicket(ticket, event)
    try:
        pdf_bytes = generate_ticket_pdf(t_obj)
    except Exception as e:
        raise HTTPException(500, f"Failed to generate PDF ticket: {str(e)}")

    headers = {
        "Content-Disposition": f"attachment; filename=ticket-{ticket_code[:8].lower()}.pdf"
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


# ── Compatibility & Scan Endpoints ────────────────────────────────────────────

@router.get("/users/me/tickets")
def get_my_tickets(current_user: AttrDict = Depends(get_current_user)):
    user_email = current_user.get("email")
    if not user_email:
        return []

    tickets = dynamodb_helper.list_tickets_by_email(user_email)
    result = []
    for t in tickets:
        event = None
        event_id = t.get("event_id")
        if not event_id and t.get("order_id"):
            order = dynamodb_helper.get_order(t["order_id"])
            if order:
                event_id = order.get("event_id")

        if event_id:
            event = dynamodb_helper.get_event(event_id)

        result.append({
            "id": t.get("TicketID") or t.get("id"),
            "registration_id": t.get("order_id", ""),
            "ticket_code": t.get("ticket_code"),
            "qr_image_url": t.get("qr_image_url"),
            "is_used": t.get("is_used", False),
            "used_at": t.get("used_at"),
            "issued_at": t.get("issued_at"),
            "event": {
                "id": event_id,
                "title": event.get("title") if event else "Event",
                "location": event.get("venue_name") if event else "Online",
                "starts_at": event.get("starts_at") if event else None,
                "ends_at": event.get("ends_at") if event else None,
                "price": str(t.get("unit_price", "0.00")),
            } if event else None,
        })
    return result


@router.post("/{ticket_code}/validate")
def validate_and_checkin_ticket(ticket_code: str):
    from app.routers.checkin import _do_scan
    res = _do_scan(ticket_code)
    return res
