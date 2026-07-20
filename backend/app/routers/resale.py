"""Resale marketplace router."""
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.models import (
    Ticket, TicketStatus, ResaleListing, ResaleStatus, OrderItem, Event,
)
from app.schemas.schemas import (
    ResaleListingCreate, ResaleListingResponse, ResalePurchase,
)
from app.core.qr import upload_qr_to_s3

router = APIRouter()


@router.get("", response_model=list[ResaleListingResponse])
def browse_resale(
    event_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(ResaleListing).filter(ResaleListing.status == ResaleStatus.active)
    if event_id:
        query = query.join(Ticket).join(OrderItem).filter(
            OrderItem.order.has(event_id=event_id)
        )
    return query.order_by(ResaleListing.listed_at.desc()).all()


@router.get("/{listing_id}", response_model=ResaleListingResponse)
def get_listing(listing_id: str, db: Session = Depends(get_db)):
    listing = db.query(ResaleListing).filter(ResaleListing.id == listing_id).first()
    if not listing:
        raise HTTPException(404, "Listing not found")
    return listing


@router.post("/tickets/{ticket_code}", response_model=ResaleListingResponse, status_code=201)
def list_for_resale(
    ticket_code: str,
    body: ResaleListingCreate,
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(Ticket.ticket_code == ticket_code).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    event = ticket.order_item.order.event
    if not event.allow_resale:
        raise HTTPException(400, "Resale is not enabled for this event")

    if ticket.status != TicketStatus.active:
        raise HTTPException(400, f"Ticket is not eligible for resale (status: {ticket.status.value})")

    # Check active or pending listing doesn't already exist
    existing = db.query(ResaleListing).filter(
        ResaleListing.ticket_id == ticket.id,
        ResaleListing.status.in_([ResaleStatus.active, ResaleStatus.pending]),
    ).first()
    if existing:
        raise HTTPException(400, "Ticket is already listed or pending resale approval")

    # Enforce max price cap
    face_value = ticket.order_item.unit_price
    max_markup = event.max_resale_markup_percent or Decimal("10.00")
    max_price = face_value * (1 + max_markup / 100)
    if body.asking_price > max_price:
        raise HTTPException(400, f"Asking price exceeds maximum allowed resale price (${max_price:.2f})")

    from app.models.models import PlatformSettings
    require_approval_setting = db.query(PlatformSettings).filter(PlatformSettings.key == "require_resale_approval").first()
    require_approval = require_approval_setting.value.lower() == "true" if require_approval_setting else False

    listing = ResaleListing(
        ticket_id=ticket.id,
        seller_name=body.seller_name,
        seller_email=body.seller_email,
        asking_price=body.asking_price,
        face_value=face_value,
        status=ResaleStatus.pending if require_approval else ResaleStatus.active,
    )
    db.add(listing)
    ticket.status = TicketStatus.resold  # temporarily mark while listed/pending
    db.commit()
    db.refresh(listing)
    return listing


@router.delete("/tickets/{ticket_code}")
def remove_listing(ticket_code: str, seller_email: str, db: Session = Depends(get_db)):
    """Remove an active resale listing (seller must provide their email)."""
    ticket = db.query(Ticket).filter(Ticket.ticket_code == ticket_code).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    listing = db.query(ResaleListing).filter(
        ResaleListing.ticket_id == ticket.id,
        ResaleListing.status == ResaleStatus.active,
        ResaleListing.seller_email == seller_email,
    ).first()
    if not listing:
        raise HTTPException(404, "Active listing not found")

    listing.status = ResaleStatus.removed
    ticket.status = TicketStatus.active
    db.commit()
    return {"message": "Listing removed"}


@router.post("/{listing_id}/purchase", status_code=201)
def purchase_resale_ticket(
    listing_id: str,
    body: ResalePurchase,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    listing = db.query(ResaleListing).filter(
        ResaleListing.id == listing_id,
        ResaleListing.status == ResaleStatus.active,
    ).first()
    if not listing:
        raise HTTPException(404, "Listing not found or no longer available")

    original_ticket = listing.ticket
    event = original_ticket.order_item.order.event

    # Invalidate original ticket
    original_ticket.status = TicketStatus.resold

    # Issue new ticket to buyer
    new_ticket = Ticket(
        order_item_id=original_ticket.order_item_id,
        attendee_name=body.buyer_name,
        attendee_email=body.buyer_email,
        status=TicketStatus.active,
    )
    db.add(new_ticket)
    db.flush()

    # Update listing
    listing.status = ResaleStatus.sold
    listing.sold_at = datetime.now(timezone.utc).replace(tzinfo=None)
    listing.buyer_name = body.buyer_name
    listing.buyer_email = body.buyer_email
    listing.buyer_ticket_id = new_ticket.id

    db.commit()
    db.refresh(new_ticket)

    background_tasks.add_task(_generate_qr, new_ticket.id)
    background_tasks.add_task(
        _send_resale_emails,
        listing.seller_email, listing.seller_name,
        body.buyer_email, body.buyer_name,
        event.title, new_ticket.ticket_code, str(listing.asking_price),
    )

    return {"message": "Purchase successful", "ticket_code": new_ticket.ticket_code}


def _generate_qr(ticket_id: str):
    from app.db.base import SessionLocal
    db = SessionLocal()
    try:
        t = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if t:
            t.qr_image_url = upload_qr_to_s3(t.ticket_code)
            db.commit()
    except Exception as e:
        print(f"[QR] resale ticket: {e}")
    finally:
        db.close()


def _send_resale_emails(seller_email, seller_name, buyer_email, buyer_name, event_title, ticket_code, price):
    try:
        from app.core.email import send_email
        send_email(
            seller_email, f"Your ticket has been sold – {event_title}",
            f"<p>Hi {seller_name}, your resale ticket for <strong>{event_title}</strong> sold for ${price}. Funds will be processed shortly.</p>",
        )
        send_email(
            buyer_email, f"Your resale ticket – {event_title}",
            f"<p>Hi {buyer_name}, you purchased a resale ticket for <strong>{event_title}</strong>. Code: <code>{ticket_code}</code></p>",
        )
    except Exception as e:
        print(f"[EMAIL] Resale notification: {e}")
