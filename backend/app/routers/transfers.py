"""Ticket transfer router."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.models import Ticket, TicketTransfer, TicketStatus, Order, OrderItem, Event
from app.schemas.schemas import TransferRequest, TransferResponse

router = APIRouter()


@router.post("/{ticket_code}/transfer", response_model=TransferResponse, status_code=201)
def transfer_ticket(
    ticket_code: str,
    body: TransferRequest,
    background_tasks: BackgroundTasks,
    guest_email: str | None = None,   # caller must prove ownership via email
    db: Session = Depends(get_db),
):
    """
    Transfer a ticket to a new owner.
    Guest ownership is proven by providing the guest_email query param matching the order email.
    """
    ticket = db.query(Ticket).filter(Ticket.ticket_code == ticket_code).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    order = ticket.order_item.order
    event = order.event

    # Verify ownership
    if guest_email and order.guest_email.lower() != guest_email.lower():
        raise HTTPException(403, "Email does not match this ticket's order")

    # Check event allows transfers
    if not event.allow_transfers:
        raise HTTPException(400, "The organizer has disabled ticket transfers for this event")

    # Check deadline
    deadline = event.starts_at - timedelta(hours=event.transfer_deadline_hours or 24)
    if datetime.now(timezone.utc).replace(tzinfo=None) > deadline:
        raise HTTPException(400, "Transfer deadline has passed")

    # Check ticket state
    if ticket.status != TicketStatus.active:
        raise HTTPException(400, f"Ticket cannot be transferred (status: {ticket.status.value})")
    if ticket.is_used:
        raise HTTPException(400, "Cannot transfer a used ticket")

    # Check transfer count
    completed_transfers = db.query(TicketTransfer).filter(
        TicketTransfer.ticket_id == ticket.id,
        TicketTransfer.is_completed == True,
    ).count()
    max_transfers = event.max_transfers_per_ticket or 1
    if completed_transfers >= max_transfers:
        raise HTTPException(400, f"This ticket has reached the maximum number of transfers ({max_transfers})")

    # Record transfer, update ticket ownership info
    transfer = TicketTransfer(
        ticket_id=ticket.id,
        from_name=ticket.attendee_name or order.guest_name,
        from_email=ticket.attendee_email or order.guest_email,
        to_name=body.to_name,
        to_email=body.to_email,
        is_completed=True,
        transferred_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(transfer)

    ticket.attendee_name = body.to_name
    ticket.attendee_email = body.to_email
    ticket.status = TicketStatus.active   # still active, new owner

    db.commit()
    db.refresh(transfer)

    background_tasks.add_task(
        _send_transfer_emails,
        transfer.from_email, transfer.from_name,
        transfer.to_email, transfer.to_name,
        event.title, ticket.ticket_code,
    )

    return transfer


@router.get("/{ticket_code}/transfers", response_model=list[TransferResponse])
def get_transfer_history(ticket_code: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.ticket_code == ticket_code).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return db.query(TicketTransfer).filter(TicketTransfer.ticket_id == ticket.id).all()


def _send_transfer_emails(from_email, from_name, to_email, to_name, event_title, ticket_code):
    try:
        from app.core.email import send_email
        send_email(
            from_email,
            f"Ticket Transferred – {event_title}",
            f"<p>Hi {from_name}, your ticket <code>{ticket_code}</code> for <strong>{event_title}</strong> has been transferred to {to_name} ({to_email}).</p>",
        )
        send_email(
            to_email,
            f"You received a ticket – {event_title}",
            f"<p>Hi {to_name}, you received a ticket for <strong>{event_title}</strong>. Ticket code: <code>{ticket_code}</code></p>",
        )
    except Exception as e:
        print(f"[EMAIL] Transfer notification failed: {e}")
