"""Check-in / QR scan router."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.models import Ticket, TicketStatus
from app.schemas.schemas import CheckInRequest, CheckInResponse, TicketResponse
from app.core.dependencies import get_current_admin, get_current_organizer

router = APIRouter()


def _do_scan(ticket_code: str, db: Session) -> CheckInResponse:
    ticket = db.query(Ticket).filter(Ticket.ticket_code == ticket_code).first()
    if not ticket:
        return CheckInResponse(valid=False, message="Ticket not found")

    if ticket.status != TicketStatus.active:
        return CheckInResponse(
            valid=False,
            message=f"Ticket is not valid (status: {ticket.status.value})",
            ticket=TicketResponse.model_validate(ticket),
        )

    if ticket.is_used:
        return CheckInResponse(
            valid=False,
            message=f"Ticket already used at {ticket.used_at}",
            ticket=TicketResponse.model_validate(ticket),
            attendee_name=ticket.attendee_name,
        )

    event = ticket.order_item.order.event
    if event.starts_at.date() != datetime.now(timezone.utc).date():
        # Allow check-in on event day only (can be relaxed)
        pass  # Remove this check if multi-day or early check-in needed

    # Mark as used
    ticket.is_used = True
    ticket.used_at = datetime.now(timezone.utc).replace(tzinfo=None)
    ticket.status = TicketStatus.used
    db.commit()
    db.refresh(ticket)

    return CheckInResponse(
        valid=True,
        message="✅ Check-in successful! Welcome!",
        ticket=TicketResponse.model_validate(ticket),
        attendee_name=ticket.attendee_name,
        ticket_type_name=ticket.ticket_type.name if ticket.ticket_type else None,
        event_title=event.title,
    )


@router.post("/scan", response_model=CheckInResponse)
def scan_ticket(
    body: CheckInRequest,
    db: Session = Depends(get_db),
):
    """
    Scan a QR code for event check-in.
    In production, restrict this to authenticated organizers/staff.
    """
    return _do_scan(body.ticket_code, db)


@router.get("/ticket/{ticket_code}", response_model=CheckInResponse)
def lookup_for_checkin(ticket_code: str, db: Session = Depends(get_db)):
    """Manual code lookup without marking as used (preview only)."""
    ticket = db.query(Ticket).filter(Ticket.ticket_code == ticket_code).first()
    if not ticket:
        return CheckInResponse(valid=False, message="Ticket not found")

    event = ticket.order_item.order.event
    return CheckInResponse(
        valid=ticket.status == TicketStatus.active and not ticket.is_used,
        message="Ticket found" if not ticket.is_used else f"Already checked in at {ticket.used_at}",
        ticket=TicketResponse.model_validate(ticket),
        attendee_name=ticket.attendee_name,
        ticket_type_name=ticket.ticket_type.name if ticket.ticket_type else None,
        event_title=event.title,
    )
