"""Resale marketplace router using DynamoDB."""
import uuid
import secrets
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

from app.db.dynamodb import dynamodb_helper
from app.schemas.schemas import (
    ResaleListingCreate, ResaleListingResponse, ResalePurchase,
)
from app.core.qr import upload_qr_to_s3
from app.core.email import send_email

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


def _format_resale_response(listing: Dict[str, Any]) -> ResaleListingResponse:
    l_id = listing.get("ListingID") or listing.get("id", "")
    return ResaleListingResponse(
        id=l_id,
        ticket_id=listing.get("ticket_id", ""),
        seller_name=listing.get("seller_name", ""),
        seller_email=listing.get("seller_email", ""),
        asking_price=Decimal(str(listing.get("asking_price", 0))),
        face_value=Decimal(str(listing.get("face_value", 0))),
        status=listing.get("status", "active"),
        listed_at=_format_dt(listing.get("listed_at")) or datetime.now(timezone.utc),
        sold_at=_format_dt(listing.get("sold_at")),
        buyer_name=listing.get("buyer_name"),
        buyer_email=listing.get("buyer_email"),
        buyer_ticket_id=listing.get("buyer_ticket_id"),
    )


@router.get("/listings", response_model=list[ResaleListingResponse])
@router.get("", response_model=list[ResaleListingResponse])
def browse_resale(event_id: str | None = Query(None)):
    listings = dynamodb_helper.list_resale_listings_by_status("active")
    
    if event_id:
        filtered = []
        for l in listings:
            t = dynamodb_helper.get_ticket(l.get("ticket_id", ""))
            if t:
                o_id = t.get("order_id")
                if o_id:
                    order = dynamodb_helper.get_order(o_id)
                    if order and order.get("event_id") == event_id:
                        filtered.append(l)
        listings = filtered

    listings.sort(key=lambda x: x.get("listed_at", ""), reverse=True)
    return [_format_resale_response(l) for l in listings]


@router.get("/{listing_id}", response_model=ResaleListingResponse)
def get_listing(listing_id: str):
    listing = dynamodb_helper.get_resale_listing(listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    return _format_resale_response(listing)


@router.post("/tickets/{ticket_code}", response_model=ResaleListingResponse, status_code=201)
def list_for_resale(ticket_code: str, body: ResaleListingCreate):
    ticket = dynamodb_helper.get_ticket_by_code(ticket_code)
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    ticket_id = str(ticket.get("TicketID") or ticket.get("id") or "")
    order = dynamodb_helper.get_order(ticket.get("order_id", "")) or {}
    event = dynamodb_helper.get_event(order.get("event_id", "") or ticket.get("event_id", "")) or {}

    if not event.get("allow_resale", True):
        raise HTTPException(400, "Resale is not enabled for this event")

    if ticket.get("status") != "active":
        raise HTTPException(400, f"Ticket is not eligible for resale (status: {ticket.get('status')})")

    # Check active or pending listing doesn't exist
    existing = dynamodb_helper.list_resale_listings_by_ticket(ticket_id)
    for e in existing:
        if e.get("status") in ("active", "pending"):
            raise HTTPException(400, "Ticket is already listed or pending resale approval")

    face_value = Decimal(str(ticket.get("unit_price", "0.00")))
    max_markup = Decimal(str(event.get("max_resale_markup_percent", "10.00")))
    max_price = face_value * (Decimal("1") + max_markup / Decimal("100"))

    if body.asking_price > max_price and max_price > Decimal("0.00"):
        raise HTTPException(400, f"Asking price exceeds maximum allowed resale price (${max_price:.2f})")

    req_setting = dynamodb_helper.get_platform_setting("require_resale_approval")
    require_approval = str(req_setting.get("value", "")).lower() == "true" if req_setting else False

    listing_id = str(uuid.uuid4())
    status_str = "pending" if require_approval else "active"

    listing_data = dynamodb_helper.create_resale_listing(listing_id, {
        "ticket_id": ticket_id,
        "seller_name": body.seller_name,
        "seller_email": body.seller_email,
        "asking_price": str(body.asking_price),
        "face_value": str(face_value),
        "status": status_str,
        "listed_at": datetime.now(timezone.utc).isoformat(),
    })

    # Temporarily update ticket status
    dynamodb_helper.update_ticket(ticket_id, {"status": "resold"})

    return _format_resale_response(listing_data)


@router.delete("/tickets/{ticket_code}")
def remove_listing(ticket_code: str, seller_email: str):
    ticket = dynamodb_helper.get_ticket_by_code(ticket_code)
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    ticket_id = str(ticket.get("TicketID") or ticket.get("id") or "")
    listings = dynamodb_helper.list_resale_listings_by_ticket(ticket_id)

    active_l = None
    for l in listings:
        if l.get("status") == "active" and l.get("seller_email", "").lower() == seller_email.lower():
            active_l = l
            break

    if not active_l:
        raise HTTPException(404, "Active listing not found")

    l_id = str(active_l.get("ListingID") or active_l.get("id") or "")
    dynamodb_helper.update_resale_listing(l_id, {"status": "removed"})
    dynamodb_helper.update_ticket(ticket_id, {"status": "active"})

    return {"message": "Listing removed"}


@router.post("/{listing_id}/purchase", status_code=201)
def purchase_resale_ticket(
    listing_id: str,
    body: ResalePurchase,
    background_tasks: BackgroundTasks,
):
    listing = dynamodb_helper.get_resale_listing(listing_id)
    if not listing or listing.get("status") != "active":
        raise HTTPException(404, "Listing not found or no longer available")

    ticket_id = str(listing.get("ticket_id") or "")
    original_ticket = dynamodb_helper.get_ticket(ticket_id) or {}
    order = dynamodb_helper.get_order(original_ticket.get("order_id", "")) or {}
    event = dynamodb_helper.get_event(order.get("event_id", "") or original_ticket.get("event_id", "")) or {}

    # Invalidate original ticket
    dynamodb_helper.update_ticket(ticket_id, {"status": "resold"})

    # Issue new ticket to buyer
    new_ticket_id = str(uuid.uuid4())
    new_code = f"AP-{secrets.token_hex(4).upper()}"
    new_ticket_data = {
        "TicketID": new_ticket_id,
        "id": new_ticket_id,
        "order_item_id": original_ticket.get("order_item_id"),
        "order_id": original_ticket.get("order_id"),
        "event_id": original_ticket.get("event_id"),
        "ticket_code": new_code,
        "attendee_name": body.buyer_name,
        "attendee_email": body.buyer_email,
        "status": "active",
        "is_used": False,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    dynamodb_helper.create_ticket(new_ticket_id, new_ticket_data)

    # Update listing
    dynamodb_helper.update_resale_listing(listing_id, {
        "status": "sold",
        "sold_at": datetime.now(timezone.utc).isoformat(),
        "buyer_name": body.buyer_name,
        "buyer_email": body.buyer_email,
        "buyer_ticket_id": new_ticket_id,
    })

    # Generate QR & send notification
    try:
        qr_url = upload_qr_to_s3(new_code)
        dynamodb_helper.update_ticket(new_ticket_id, {"qr_image_url": qr_url})
    except Exception as e:
        print(f"[QR] resale ticket: {e}")

    _send_resale_emails(
        listing.get("seller_email"), listing.get("seller_name"),
        body.buyer_email, body.buyer_name,
        event.get("title", "Event"), new_code, str(listing.get("asking_price")),
    )

    return {"message": "Purchase successful", "ticket_code": new_code}


def _send_resale_emails(seller_email, seller_name, buyer_email, buyer_name, event_title, ticket_code, price):
    try:
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
