"""Check-in / QR scan router using DynamoDB."""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.db.dynamodb import dynamodb_helper
from app.schemas.schemas import CheckInRequest, CheckInResponse, TicketResponse
from app.core.dependencies import get_current_organizer, get_current_user, optional_bearer, AttrDict
from app.core.utils import format_dt as _format_dt

router = APIRouter()





def _format_ticket_response(ticket: Dict[str, Any]) -> TicketResponse:
    t_id = ticket.get("TicketID") or ticket.get("id", "")
    return TicketResponse(
        id=t_id,
        order_item_id=ticket.get("order_item_id", ""),
        ticket_code=ticket.get("ticket_code", ""),
        qr_image_url=ticket.get("qr_image_url"),
        status=ticket.get("status", "active"),
        is_used=ticket.get("is_used", False),
        used_at=_format_dt(ticket.get("used_at")),
        attendee_name=ticket.get("attendee_name"),
        attendee_email=ticket.get("attendee_email"),
        issued_at=_format_dt(ticket.get("issued_at")) or datetime.now(timezone.utc),
    )


def _do_scan(ticket_code: str) -> CheckInResponse:
    ticket = dynamodb_helper.get_ticket_by_code(ticket_code)
    if not ticket:
        return CheckInResponse(valid=False, message="Ticket not found")

    status_val = ticket.get("status", "active")
    if status_val != "active":
        return CheckInResponse(
            valid=False,
            message=f"Ticket is not valid (status: {status_val})",
            ticket=_format_ticket_response(ticket),
        )

    if ticket.get("is_used", False):
        return CheckInResponse(
            valid=False,
            message=f"Ticket already used at {ticket.get('used_at')}",
            ticket=_format_ticket_response(ticket),
            attendee_name=ticket.get("attendee_name"),
        )

    event = None
    event_id = ticket.get("event_id")
    if not event_id and ticket.get("order_id"):
        order = dynamodb_helper.get_order(ticket["order_id"])
        if order:
            event_id = order.get("event_id")

    if event_id:
        event = dynamodb_helper.get_event(event_id)

    # Mark as used
    t_id = str(ticket.get("TicketID") or ticket.get("id") or "")
    used_now = datetime.now(timezone.utc).isoformat()
    
    dynamodb_helper.update_ticket(t_id, {
        "is_used": True,
        "used_at": used_now,
        "status": "used",
    })
    
    ticket["is_used"] = True
    ticket["used_at"] = used_now
    ticket["status"] = "used"

    return CheckInResponse(
        valid=True,
        message="✅ Check-in successful! Welcome!",
        ticket=_format_ticket_response(ticket),
        attendee_name=ticket.get("attendee_name"),
        ticket_type_name=ticket.get("ticket_type_name"),
        event_title=event.get("title") if event else None,
    )


@router.post("/scan", response_model=CheckInResponse)
def scan_ticket(
    body: CheckInRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
):
    """
    Scan a QR code for event check-in.
    """
    return _do_scan(body.ticket_code)


@router.get("/ticket/{ticket_code}", response_model=CheckInResponse)
def lookup_for_checkin(ticket_code: str):
    """Manual code lookup without marking as used (preview only)."""
    ticket = dynamodb_helper.get_ticket_by_code(ticket_code)
    if not ticket:
        return CheckInResponse(valid=False, message="Ticket not found")

    event = None
    event_id = ticket.get("event_id")
    if not event_id and ticket.get("order_id"):
        order = dynamodb_helper.get_order(ticket["order_id"])
        if order:
            event_id = order.get("event_id")

    if event_id:
        event = dynamodb_helper.get_event(event_id)

    is_active = (ticket.get("status") == "active") and (not ticket.get("is_used", False))
    used_at = ticket.get("used_at")

    return CheckInResponse(
        valid=is_active,
        message="Ticket found" if not ticket.get("is_used") else f"Already checked in at {used_at}",
        ticket=_format_ticket_response(ticket),
        attendee_name=ticket.get("attendee_name"),
        ticket_type_name=ticket.get("ticket_type_name"),
        event_title=event.get("title") if event else None,
    )
