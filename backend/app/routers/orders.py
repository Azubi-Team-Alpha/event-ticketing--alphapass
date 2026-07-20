"""Guest checkout – single ticket and bulk/group order purchases."""
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.models import (
    Event, EventStatus, TicketType, PromoCode, Order, OrderItem, Ticket,
    OrderStatus, TicketStatus, DiscountType, AuditLog,
)
from app.schemas.schemas import (
    OrderCreate, OrderResponse, OrderLookup, AttendeeUpdate,
    PromoCodeValidation, ApplyPromoCode, RefundRequest,
)
from app.core.config import settings
from app.core.qr import upload_qr_to_s3

router = APIRouter()


def _apply_promo(promo: PromoCode, subtotal: Decimal) -> Decimal:
    """Returns the discount amount to subtract."""
    if promo.discount_type == DiscountType.percentage:
        return (subtotal * promo.discount_value / 100).quantize(Decimal("0.01"))
    else:
        return min(Decimal(str(promo.discount_value)), subtotal)


# ── Promo code validation (public endpoint) ───────────────────────────────────

@router.post("/validate-promo", response_model=PromoCodeValidation)
def validate_promo(body: ApplyPromoCode, db: Session = Depends(get_db)):
    promo = db.query(PromoCode).filter(
        PromoCode.event_id == body.event_id,
        PromoCode.code == body.code.upper(),
        PromoCode.is_active == True,
    ).first()
    if not promo:
        return PromoCodeValidation(valid=False, message="Invalid or expired promo code")
    if promo.expires_at and promo.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        return PromoCodeValidation(valid=False, message="Promo code has expired")
    if promo.max_uses and promo.used_count >= promo.max_uses:
        return PromoCodeValidation(valid=False, message="Promo code usage limit reached")
    return PromoCodeValidation(
        valid=True, message="Promo code applied",
        discount_type=promo.discount_type.value,
        discount_value=Decimal(str(promo.discount_value)),
    )


# ── Create Order (Guest Checkout) ─────────────────────────────────────────────

@router.post("", response_model=OrderResponse, status_code=201)
def create_order(
    body: OrderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # 1. Validate event
    event = db.query(Event).filter(Event.id == body.event_id).first()
    if not event or event.status != EventStatus.published:
        raise HTTPException(404, "Event not found or not available")
    if event.starts_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(400, "Event has already started")

    # 2. Validate ticket types & availability
    subtotal = Decimal("0.00")
    item_data = []
    for item in body.items:
        tt = db.query(TicketType).filter(
            TicketType.id == item.ticket_type_id,
            TicketType.event_id == body.event_id,
            TicketType.is_active == True,
        ).with_for_update().first()
        if not tt:
            raise HTTPException(404, f"Ticket type {item.ticket_type_id} not found")
        if tt.quantity_remaining < item.quantity:
            raise HTTPException(400, f"Not enough tickets available for '{tt.name}' (requested {item.quantity}, available {tt.quantity_remaining})")
        if item.quantity > tt.purchase_limit:
            raise HTTPException(400, f"Maximum {tt.purchase_limit} tickets per order for '{tt.name}'")
        if item.quantity < tt.min_purchase:
            raise HTTPException(400, f"Minimum {tt.min_purchase} tickets required for '{tt.name}'")
        line = Decimal(str(tt.price)) * item.quantity
        subtotal += line
        item_data.append((tt, item, line))

    # 3. Apply promo code
    promo = None
    discount = Decimal("0.00")
    if body.promo_code:
        promo = db.query(PromoCode).filter(
            PromoCode.event_id == body.event_id,
            PromoCode.code == body.promo_code.upper(),
            PromoCode.is_active == True,
        ).first()
        if not promo:
            raise HTTPException(400, "Invalid promo code")
        if promo.expires_at and promo.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
            raise HTTPException(400, "Promo code has expired")
        if promo.max_uses and promo.used_count >= promo.max_uses:
            raise HTTPException(400, "Promo code usage limit reached")
        discount = _apply_promo(promo, subtotal)

    # 4. Calculate fees
    total_quantity = sum(item.quantity for item in body.items)
    if event.group_discount_threshold and total_quantity >= event.group_discount_threshold and event.group_discount_percent:
        group_discount = (subtotal * (Decimal(str(event.group_discount_percent)) / 100)).quantize(Decimal("0.01"))
        discount += group_discount

    commission = Decimal(str(settings.PLATFORM_COMMISSION_PERCENT)) / 100
    taxable = max(Decimal("0.00"), subtotal - discount)
    platform_fee = (taxable * commission).quantize(Decimal("0.01"))
    total = taxable + platform_fee

    # 5. Create order
    order = Order(
        event_id=body.event_id,
        promo_code_id=promo.id if promo else None,
        guest_name=body.guest_name,
        guest_email=body.guest_email,
        guest_phone=body.guest_phone,
        status=OrderStatus.confirmed,  # would be 'pending' until payment webhook in prod
        subtotal=subtotal,
        discount_amount=discount,
        platform_fee=platform_fee,
        total_amount=total,
        payment_reference=body.payment_reference,
        payment_method=body.payment_method,
    )
    db.add(order)
    db.flush()

    # 6. Create order items + tickets
    all_tickets = []
    for tt, item, line in item_data:
        oi = OrderItem(
            order_id=order.id,
            ticket_type_id=tt.id,
            quantity=item.quantity,
            unit_price=tt.price,
            line_total=line,
        )
        db.add(oi)
        db.flush()

        for i in range(item.quantity):
            ticket = Ticket(
                order_item_id=oi.id,
                attendee_name=item.attendee_name or body.guest_name,
                attendee_email=item.attendee_email or body.guest_email,
                status=TicketStatus.active,
            )
            db.add(ticket)
            db.flush()
            all_tickets.append(ticket)

        # Update sold count
        tt.quantity_sold += item.quantity  # type: ignore

    # 7. Update promo usage
    if promo:
        promo.used_count += 1  # type: ignore

    db.commit()
    db.refresh(order)

    # 8. Generate QR codes in background
    background_tasks.add_task(_generate_qr_codes, [t.id for t in all_tickets])

    # 9. Send confirmation email
    background_tasks.add_task(
        _send_order_confirmation,
        order.guest_email, order.guest_name, event.title,
        order.id, len(all_tickets), str(order.total_amount),
    )

    return order


# ── Lookup Order ──────────────────────────────────────────────────────────────

@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@router.post("/lookup", response_model=OrderResponse)
def lookup_order(body: OrderLookup, db: Session = Depends(get_db)):
    """Guest re-download: find order by ID + email."""
    order = db.query(Order).filter(
        Order.id == body.order_id,
        Order.guest_email == body.guest_email,
    ).first()
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@router.put("/{order_id}/cancel")
def cancel_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.status != OrderStatus.confirmed:
        raise HTTPException(400, "Only confirmed orders can be cancelled")
    order.status = OrderStatus.cancelled  # type: ignore
    for item in order.items:
        item.ticket_type.quantity_sold = max(0, item.ticket_type.quantity_sold - item.quantity)  # type: ignore
        for ticket in item.tickets:
            ticket.status = TicketStatus.cancelled  # type: ignore
    db.commit()
    return {"message": "Order cancelled"}


# ── Update attendee info ──────────────────────────────────────────────────────

@router.put("/{order_id}/tickets/{ticket_id}/attendee", response_model=dict)
def update_attendee(
    order_id: str, ticket_id: str,
    body: AttendeeUpdate, db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket or ticket.order_item.order_id != order_id:
        raise HTTPException(404, "Ticket not found in this order")
    ticket.attendee_name = body.attendee_name  # type: ignore
    if body.attendee_email:
        ticket.attendee_email = str(body.attendee_email)  # type: ignore
    db.commit()
    return {"message": "Attendee info updated"}


# ── Organizer: view orders for an event ──────────────────────────────────────

@router.get("/event/{event_id}", response_model=list[OrderResponse])
def event_orders(
    event_id: str,
    is_bulk: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    from app.core.dependencies import get_current_organizer
    query = db.query(Order).filter(Order.event_id == event_id)
    if is_bulk is not None:
        from sqlalchemy import func
        subq = db.query(OrderItem.order_id).group_by(OrderItem.order_id).having(func.sum(OrderItem.quantity) >= 5).scalar_subquery()
        if is_bulk:
            query = query.filter(Order.id.in_(subq))
        else:
            query = query.filter(~Order.id.in_(subq))
    orders = query.all()
    return orders


@router.post("/{order_id}/refund-request")
def request_order_refund(
    order_id: str,
    body: RefundRequest,
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.guest_email.lower() != body.guest_email.lower():
        raise HTTPException(403, "Email does not match order guest email")
    if order.status != OrderStatus.confirmed:
        raise HTTPException(400, f"Refund can only be requested for confirmed orders (status: {order.status})")

    # Check if event allows refunds
    event = order.event
    if not event.allow_refunds:
        raise HTTPException(400, "Refunds are not allowed for this event")
    if event.starts_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(400, "Cannot request a refund after the event has started")

    # Update order status to refund_pending
    order.status = OrderStatus.refund_pending  # type: ignore
    db.add(AuditLog(
        actor_type="guest", actor_email=order.guest_email,
        action="order.refund_requested", resource_type="order", resource_id=order_id,
        meta={"reason": body.reason},
    ))
    db.commit()
    return {"message": "Refund request submitted successfully. It is now awaiting admin approval."}


# ── Background helpers ────────────────────────────────────────────────────────

def _generate_qr_codes(ticket_ids: list[str]):
    from app.db.base import SessionLocal
    db = SessionLocal()
    try:
        for tid in ticket_ids:
            ticket = db.query(Ticket).filter(Ticket.id == tid).first()
            if ticket and not ticket.qr_image_url:
                try:
                    url = upload_qr_to_s3(ticket.ticket_code)  # type: ignore
                    ticket.qr_image_url = url  # type: ignore
                except Exception as e:
                    print(f"[QR] Failed for ticket {tid}: {e}")
        db.commit()
    finally:
        db.close()


def _send_order_confirmation(email, name, event_title, order_id, ticket_count, total):
    try:
        from app.core.email import send_email
        html = (
            f"<h2>Order Confirmed! 🎉</h2>"
            f"<p>Hi {name}, your order for <strong>{event_title}</strong> is confirmed.</p>"
            f"<p>Order ID: <code>{order_id}</code></p>"
            f"<p>Tickets: {ticket_count} | Total: ${total}</p>"
            f"<p>Your QR-code tickets will be attached shortly.</p>"
        )
        send_email(email, f"Order Confirmed – {event_title}", html)
    except Exception as e:
        print(f"[EMAIL] Order confirmation failed: {e}")
