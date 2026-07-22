"""Guest checkout – single ticket and bulk/group order purchases using DynamoDB."""
import uuid
import secrets
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query

from app.db.dynamodb import dynamodb_helper
from app.schemas.schemas import (
    OrderCreate, OrderResponse, OrderLookup, AttendeeUpdate,
    PromoCodeValidation, ApplyPromoCode, RefundRequest,
)
from app.core.config import settings
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


def _apply_promo(promo: Dict[str, Any], subtotal: Decimal) -> Decimal:
    disc_type = promo.get("discount_type", "percentage")
    disc_val = Decimal(str(promo.get("discount_value", 0)))
    if disc_type == "percentage":
        return (subtotal * disc_val / Decimal("100")).quantize(Decimal("0.01"))
    else:
        return min(disc_val, subtotal)


def _format_order_response(order: Dict[str, Any]) -> Dict[str, Any]:
    order_id = order.get("OrderID") or order.get("id")
    event_id = order.get("event_id", "")
    event = dynamodb_helper.get_event(event_id) or {}
    
    items = order.get("items", [])
    tickets = order.get("tickets", [])

    formatted_items = []
    for item in items:
        oi_id = item.get("id") or str(uuid.uuid4())
        tt_id = item.get("ticket_type_id", "")
        tt_name = item.get("ticket_type_name", "Standard")
        
        item_tickets = [t for t in tickets if t.get("order_item_id") == oi_id or t.get("ticket_type_id") == tt_id]
        
        formatted_tix = []
        for t in item_tickets:
            formatted_tix.append({
                "id": t.get("TicketID") or t.get("id", str(uuid.uuid4())),
                "order_item_id": oi_id,
                "ticket_code": t.get("ticket_code", ""),
                "qr_image_url": t.get("qr_image_url"),
                "status": t.get("status", "active"),
                "is_used": t.get("is_used", False),
                "used_at": _format_dt(t.get("used_at")),
                "attendee_name": t.get("attendee_name"),
                "attendee_email": t.get("attendee_email"),
                "issued_at": _format_dt(t.get("issued_at")) or datetime.now(timezone.utc),
            })

        formatted_items.append({
            "id": oi_id,
            "order_id": order_id,
            "ticket_type_id": tt_id,
            "quantity": int(item.get("quantity", 1)),
            "unit_price": Decimal(str(item.get("unit_price", 0))),
            "line_total": Decimal(str(item.get("line_total", 0))),
            "ticket_type": {
                "id": tt_id,
                "event_id": event_id,
                "name": tt_name,
                "price": Decimal(str(item.get("unit_price", 0))),
                "quantity": int(item.get("quantity", 1)),
                "quantity_sold": 0,
                "purchase_limit": 10,
                "min_purchase": 1,
                "is_active": True,
                "sort_order": 0,
                "quantity_remaining": 0,
                "created_at": datetime.now(timezone.utc),
            },
            "tickets": formatted_tix,
        })

    all_flattened_tickets = []
    for item_resp in formatted_items:
        all_flattened_tickets.extend(item_resp.get("tickets", []))

    return {
        "id": order_id,
        "event_id": event_id,
        "promo_code_id": order.get("promo_code_id"),
        "guest_name": order.get("guest_name", ""),
        "guest_email": order.get("guest_email", ""),
        "guest_phone": order.get("guest_phone"),
        "status": order.get("status", "confirmed"),
        "subtotal": Decimal(str(order.get("subtotal", 0))),
        "discount_amount": Decimal(str(order.get("discount_amount", 0))),
        "platform_fee": Decimal(str(order.get("platform_fee", 0))),
        "total_amount": Decimal(str(order.get("total_amount", 0))),
        "payment_reference": order.get("payment_reference"),
        "payment_method": order.get("payment_method"),
        "created_at": _format_dt(order.get("created_at")) or datetime.now(timezone.utc),
        "event_title": event.get("title"),
        "total_tickets": sum(int(i.get("quantity", 1)) for i in items),
        "items": formatted_items,
        "tickets": all_flattened_tickets,
    }


# ── Promo code validation (public endpoint) ───────────────────────────────────

@router.post("/validate-promo", response_model=PromoCodeValidation)
def validate_promo(body: ApplyPromoCode):
    code_str = body.code.upper()
    promo = dynamodb_helper.get_promo_code(code_str)
    if not promo or promo.get("event_id") != body.event_id or not promo.get("is_active", True):
        return PromoCodeValidation(valid=False, message="Invalid or expired promo code")
    
    expires_at = promo.get("expires_at")
    if expires_at:
        exp_dt = _format_dt(expires_at)
        if exp_dt and exp_dt < datetime.now(timezone.utc):
            return PromoCodeValidation(valid=False, message="Promo code has expired")

    max_uses = promo.get("max_uses")
    if max_uses and int(promo.get("used_count", 0)) >= int(max_uses):
        return PromoCodeValidation(valid=False, message="Promo code usage limit reached")

    return PromoCodeValidation(
        valid=True,
        message="Promo code applied",
        discount_type=promo.get("discount_type", "percentage"),
        discount_value=Decimal(str(promo.get("discount_value", 0))),
    )


# ── Create Order (Guest Checkout) ─────────────────────────────────────────────

@router.post("", response_model=OrderResponse, status_code=201)
def create_order(
    body: OrderCreate,
    background_tasks: BackgroundTasks,
):
    # 1. Validate event
    event = dynamodb_helper.get_event(body.event_id)
    if not event or event.get("status") != "published":
        raise HTTPException(404, "Event not found or not available")
    
    starts_at = _format_dt(event.get("starts_at"))
    if starts_at and starts_at < datetime.now(timezone.utc):
        raise HTTPException(400, "Event has already started")

    # 2. Validate ticket types & availability
    ticket_types = event.get("ticket_types", [])
    subtotal = Decimal("0.00")
    order_items = []
    all_tickets = []

    for item in body.items:
        tt = next((t for t in ticket_types if t.get("id") == item.ticket_type_id and t.get("is_active", True)), None)
        if not tt:
            raise HTTPException(404, f"Ticket type '{item.ticket_type_id}' not found or inactive")

        avail = int(tt.get("quantity", 0)) - int(tt.get("quantity_sold", 0))
        if item.quantity > avail:
            raise HTTPException(400, f"Not enough tickets available for '{tt.get('name')}' ({avail} left)")
        
        limit = int(tt.get("purchase_limit", 10))
        min_p = int(tt.get("min_purchase", 1))
        if item.quantity > limit:
            raise HTTPException(400, f"Maximum {limit} tickets per order for '{tt.get('name')}'")
        if item.quantity < min_p:
            raise HTTPException(400, f"Minimum {min_p} tickets required for '{tt.get('name')}'")

        price = Decimal(str(tt.get("price", 0)))
        line = price * item.quantity
        subtotal += line

        oi_id = str(uuid.uuid4())
        order_items.append({
            "id": oi_id,
            "ticket_type_id": item.ticket_type_id,
            "ticket_type_name": tt.get("name", "Standard"),
            "quantity": item.quantity,
            "unit_price": str(price),
            "line_total": str(line),
        })

        # Update sold count on event ticket_type
        tt["quantity_sold"] = int(tt.get("quantity_sold", 0)) + item.quantity

        for _ in range(item.quantity):
            t_id = str(uuid.uuid4())
            code = f"AP-{secrets.token_hex(4).upper()}"
            t_entry = {
                "TicketID": t_id,
                "id": t_id,
                "order_item_id": oi_id,
                "ticket_type_id": item.ticket_type_id,
                "ticket_type_name": tt.get("name", "Standard"),
                "ticket_code": code,
                "attendee_name": item.attendee_name or body.guest_name,
                "attendee_email": item.attendee_email or body.guest_email,
                "status": "active",
                "is_used": False,
                "issued_at": datetime.now(timezone.utc).isoformat(),
            }
            all_tickets.append(t_entry)

    # 3. Apply promo code
    promo = None
    discount = Decimal("0.00")
    if body.promo_code:
        code_str = body.promo_code.upper()
        promo = dynamodb_helper.get_promo_code(code_str)
        if not promo or promo.get("event_id") != body.event_id:
            raise HTTPException(400, "Invalid promo code")
        discount = _apply_promo(promo, subtotal)
        dynamodb_helper.update_promo_code(code_str, {"used_count": int(promo.get("used_count", 0)) + 1})

    # 4. Group discount & platform fees
    total_quantity = sum(item.quantity for item in body.items)
    threshold = event.get("group_discount_threshold")
    grp_pct = event.get("group_discount_percent")
    if threshold and total_quantity >= int(threshold) and grp_pct:
        grp_discount = (subtotal * (Decimal(str(grp_pct)) / Decimal("100"))).quantize(Decimal("0.01"))
        discount += grp_discount

    commission = Decimal(str(settings.PLATFORM_COMMISSION_PERCENT)) / Decimal("100")
    taxable = max(Decimal("0.00"), subtotal - discount)
    platform_fee = (taxable * commission).quantize(Decimal("0.01"))
    total = taxable + platform_fee

    # 5. Create order object
    order_id = str(uuid.uuid4())
    order_data = {
        "OrderID": order_id,
        "id": order_id,
        "event_id": body.event_id,
        "promo_code_id": body.promo_code.upper() if body.promo_code else None,
        "guest_name": body.guest_name,
        "guest_email": body.guest_email,
        "guest_phone": body.guest_phone,
        "status": "confirmed",
        "subtotal": str(subtotal),
        "discount_amount": str(discount),
        "platform_fee": str(platform_fee),
        "total_amount": str(total),
        "payment_reference": body.payment_reference,
        "payment_method": body.payment_method,
        "items": order_items,
        "tickets": all_tickets,
    }

    dynamodb_helper.create_order(order_id, order_data)

    # Save individual ticket entries to tickets table for direct lookup by code
    for t in all_tickets:
        t["order_id"] = order_id
        t["event_id"] = body.event_id
        dynamodb_helper.create_ticket(t["TicketID"], t)

    # Update event ticket_types in DynamoDB
    dynamodb_helper.update_event(body.event_id, {"ticket_types": ticket_types})

    # Generate QR codes inline/sync for reliability in Lambda
    _generate_qr_and_notify(all_tickets, order_id, body.guest_email, body.guest_name, event.get("title", ""), total)

    return _format_order_response(order_data)


# ── Lookup Order ──────────────────────────────────────────────────────────────

@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: str):
    order = dynamodb_helper.get_order(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return _format_order_response(order)


@router.post("/lookup", response_model=OrderResponse)
def lookup_order(body: OrderLookup):
    order = dynamodb_helper.get_order(body.order_id)
    if not order or order.get("guest_email", "").lower() != body.guest_email.lower():
        raise HTTPException(404, "Order not found")
    return _format_order_response(order)


@router.put("/{order_id}/cancel")
def cancel_order(order_id: str):
    order = dynamodb_helper.get_order(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if order.get("status") != "confirmed":
        raise HTTPException(400, "Only confirmed orders can be cancelled")

    dynamodb_helper.update_order(order_id, {"status": "cancelled"})
    
    # Update individual tickets status
    tickets = order.get("tickets", [])
    for t in tickets:
        t_id = t.get("TicketID") or t.get("id")
        if t_id:
            dynamodb_helper.update_ticket(t_id, {"status": "cancelled"})

    return {"message": "Order cancelled"}


# ── Update attendee info ──────────────────────────────────────────────────────

@router.put("/{order_id}/tickets/{ticket_id}/attendee", response_model=dict)
def update_attendee(order_id: str, ticket_id: str, body: AttendeeUpdate):
    order = dynamodb_helper.get_order(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    
    tickets = order.get("tickets", [])
    found_t = None
    for t in tickets:
        if (t.get("TicketID") == ticket_id or t.get("id") == ticket_id):
            found_t = t
            break

    if not found_t:
        raise HTTPException(404, "Ticket not found in this order")

    found_t["attendee_name"] = body.attendee_name
    if body.attendee_email:
        found_t["attendee_email"] = str(body.attendee_email)

    dynamodb_helper.update_order(order_id, {"tickets": tickets})
    dynamodb_helper.update_ticket(ticket_id, {
        "attendee_name": body.attendee_name,
        "attendee_email": str(body.attendee_email) if body.attendee_email else found_t.get("attendee_email"),
    })

    return {"message": "Attendee info updated"}


# ── Organizer: view orders for an event ──────────────────────────────────────

@router.get("/event/{event_id}", response_model=list[OrderResponse])
def event_orders(event_id: str, is_bulk: bool | None = Query(None)):
    orders = dynamodb_helper.list_orders_by_event(event_id)
    if is_bulk is not None:
        if is_bulk:
            orders = [o for o in orders if sum(int(i.get("quantity", 1)) for i in o.get("items", [])) >= 5]
        else:
            orders = [o for o in orders if sum(int(i.get("quantity", 1)) for i in o.get("items", [])) < 5]
    return [_format_order_response(o) for o in orders]


@router.post("/{order_id}/refund-request")
def request_order_refund(order_id: str, body: RefundRequest):
    order = dynamodb_helper.get_order(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if order.get("guest_email", "").lower() != body.guest_email.lower():
        raise HTTPException(403, "Email does not match order guest email")
    if order.get("status") != "confirmed":
        raise HTTPException(400, f"Refund can only be requested for confirmed orders (status: {order.get('status')})")

    event = dynamodb_helper.get_event(order.get("event_id", ""))
    if event and not event.get("allow_refunds", True):
        raise HTTPException(400, "Refunds are not allowed for this event")

    dynamodb_helper.update_order(order_id, {"status": "refund_pending"})
    dynamodb_helper.create_audit_log({
        "actor_type": "guest",
        "actor_email": body.guest_email,
        "action": "order.refund_requested",
        "resource_type": "order",
        "resource_id": order_id,
        "meta": {"reason": body.reason},
    })
    return {"message": "Refund request submitted successfully. It is now awaiting admin approval."}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_qr_and_notify(tickets: List[Dict[str, Any]], order_id: str, email: str, name: str, event_title: str, total: Decimal):
    for t in tickets:
        code = t.get("ticket_code")
        t_id = t.get("TicketID") or t.get("id")
        if code and t_id:
            try:
                qr_url = upload_qr_to_s3(code)
                t["qr_image_url"] = qr_url
                dynamodb_helper.update_ticket(t_id, {"qr_image_url": qr_url})
            except Exception as e:
                print(f"[QR] Failed for ticket {t_id}: {e}")

    try:
        html = (
            f"<h2>Order Confirmed! 🎉</h2>"
            f"<p>Hi {name}, your order for <strong>{event_title}</strong> is confirmed.</p>"
            f"<p>Order ID: <code>{order_id}</code></p>"
            f"<p>Tickets: {len(tickets)} | Total: ${total}</p>"
            f"<p>Your QR-code tickets are available in your AlphaPass portal.</p>"
        )
        send_email(email, f"Order Confirmed – {event_title}", html)
    except Exception as e:
        print(f"[EMAIL] Order confirmation failed: {e}")
