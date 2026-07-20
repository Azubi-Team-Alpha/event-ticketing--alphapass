"""Ticket lookup routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.models import Ticket, TicketStatus
from app.schemas.schemas import TicketResponse
from app.core.dependencies import get_current_user

router = APIRouter()


@router.get("/{ticket_code}", response_model=TicketResponse)
def get_ticket(ticket_code: str, db: Session = Depends(get_db)):
    """Public ticket lookup by code (for guest re-download)."""
    ticket = db.query(Ticket).filter(Ticket.ticket_code == ticket_code).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return ticket


@router.get("/{ticket_code}/status")
def ticket_status(ticket_code: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.ticket_code == ticket_code).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    event = ticket.order_item.order.event
    return {
        "ticket_code": ticket.ticket_code,
        "status": ticket.status.value,
        "is_used": ticket.is_used,
        "used_at": ticket.used_at,
        "attendee_name": ticket.attendee_name,
        "ticket_type": ticket.ticket_type.name if ticket.ticket_type else None,
        "event_title": event.title if event else None,
        "event_starts_at": event.starts_at if event else None,
        "qr_image_url": ticket.qr_image_url,
    }


@router.get("/{ticket_code}/pdf")
def download_ticket_pdf(ticket_code: str, db: Session = Depends(get_db)):
    """Generate and download official PDF ticket."""
    from fastapi import Response
    from app.core.pdf import generate_ticket_pdf

    ticket = db.query(Ticket).filter(Ticket.ticket_code == ticket_code).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    
    try:
        pdf_bytes = generate_ticket_pdf(ticket)
    except Exception as e:
        raise HTTPException(500, f"Failed to generate PDF ticket: {str(e)}")

    headers = {
        "Content-Disposition": f"attachment; filename=ticket-{ticket_code[:8].lower()}.pdf"
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


# ── Compatibility & Scan Endpoints ────────────────────────────────────────────

@router.get("/users/me/tickets")
def get_my_tickets(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    tickets = db.query(Ticket).filter(Ticket.attendee_email == current_user.email).all()
    result = []
    for t in tickets:
        # Get order item and event safely
        oi = t.order_item
        event = oi.order.event if oi and oi.order else None
        result.append({
            "id": t.id,
            "registration_id": oi.order_id if oi else "",
            "ticket_code": t.ticket_code,
            "qr_image_url": t.qr_image_url,
            "is_used": t.is_used,
            "used_at": t.used_at,
            "issued_at": t.issued_at,
            "event": {
                "id": event.id,
                "title": event.title,
                "location": event.venue_name or "Online",
                "starts_at": event.starts_at,
                "ends_at": event.ends_at,
                "price": str(oi.unit_price) if oi else "0.00",
            } if event else None,
        })
    return result


@router.post("/{ticket_code}/validate")
def validate_and_checkin_ticket(ticket_code: str, db: Session = Depends(get_db)):
    from app.routers.checkin import _do_scan
    res = _do_scan(ticket_code, db)
    return res


