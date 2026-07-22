"""Ticket transfer router using DynamoDB."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from app.db.dynamodb import dynamodb_helper
from app.schemas.schemas import TransferRequest, TransferResponse

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


@router.post("/{ticket_code}/transfer", response_model=TransferResponse, status_code=201)
def transfer_ticket(
    ticket_code: str,
    body: TransferRequest,
    background_tasks: BackgroundTasks,
    guest_email: str | None = None,
):
    ticket = dynamodb_helper.get_ticket_by_code(ticket_code)
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    ticket_id = ticket.get("TicketID") or ticket.get("id")
    order = dynamodb_helper.get_order(ticket.get("order_id", "")) or {}
    event = dynamodb_helper.get_event(order.get("event_id", "") or ticket.get("event_id", "")) or {}

    # Verify ownership
    if guest_email and order.get("guest_email", "").lower() != guest_email.lower():
        raise HTTPException(403, "Email does not match this ticket's order")

    # Check event allows transfers
    if not event.get("allow_transfers", True):
        raise HTTPException(400, "The organizer has disabled ticket transfers for this event")

    # Check deadline
    starts_at = _format_dt(event.get("starts_at"))
    if starts_at:
        deadline_hrs = int(event.get("transfer_deadline_hours", 24))
        deadline = starts_at - timedelta(hours=deadline_hrs)
        if datetime.now(timezone.utc) > deadline:
            raise HTTPException(400, "Transfer deadline has passed")

    # Check ticket state
    if ticket.get("status") != "active":
        raise HTTPException(400, f"Ticket cannot be transferred (status: {ticket.get('status')})")
    if ticket.get("is_used", False):
        raise HTTPException(400, "Cannot transfer a used ticket")

    # Check transfer count
    transfers = dynamodb_helper.list_transfers_by_ticket(ticket_id)
    completed_transfers = [t for t in transfers if t.get("is_completed", True)]
    max_transfers = int(event.get("max_transfers_per_ticket", 1))
    if len(completed_transfers) >= max_transfers:
        raise HTTPException(400, f"This ticket has reached the maximum number of transfers ({max_transfers})")

    # Record transfer
    transfer_id = str(uuid.uuid4())
    from_name = ticket.get("attendee_name") or order.get("guest_name", "")
    from_email = ticket.get("attendee_email") or order.get("guest_email", "")

    transfer_data = dynamodb_helper.create_transfer(transfer_id, {
        "ticket_id": ticket_id,
        "from_name": from_name,
        "from_email": from_email,
        "to_name": body.to_name,
        "to_email": body.to_email,
        "is_completed": True,
        "transferred_at": datetime.now(timezone.utc).isoformat(),
    })

    # Update ticket ownership
    dynamodb_helper.update_ticket(ticket_id, {
        "attendee_name": body.to_name,
        "attendee_email": body.to_email,
        "status": "active",
    })

    # Also update order.tickets list if present in order
    if order:
        order_tickets = order.get("tickets", [])
        for ot in order_tickets:
            if ot.get("TicketID") == ticket_id or ot.get("id") == ticket_id:
                ot["attendee_name"] = body.to_name
                ot["attendee_email"] = body.to_email
        dynamodb_helper.update_order(order["OrderID"], {"tickets": order_tickets})

    _send_transfer_emails(
        from_email, from_name,
        body.to_email, body.to_name,
        event.get("title", "Event"), ticket_code,
    )

    return TransferResponse(
        id=transfer_id,
        ticket_id=ticket_id,
        from_name=from_name,
        from_email=from_email,
        to_name=body.to_name,
        to_email=body.to_email,
        is_completed=True,
        transferred_at=_format_dt(transfer_data.get("transferred_at")) or datetime.now(timezone.utc),
    )


@router.get("/{ticket_code}/transfers", response_model=list[TransferResponse])
def get_transfer_history(ticket_code: str):
    ticket = dynamodb_helper.get_ticket_by_code(ticket_code)
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    ticket_id = ticket.get("TicketID") or ticket.get("id")
    transfers = dynamodb_helper.list_transfers_by_ticket(ticket_id)
    return [
        TransferResponse(
            id=t.get("TransferID") or t.get("id", ""),
            ticket_id=ticket_id,
            from_name=t.get("from_name", ""),
            from_email=t.get("from_email", ""),
            to_name=t.get("to_name", ""),
            to_email=t.get("to_email", ""),
            is_completed=t.get("is_completed", True),
            transferred_at=_format_dt(t.get("transferred_at")) or datetime.now(timezone.utc),
        )
        for t in transfers
    ]


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
