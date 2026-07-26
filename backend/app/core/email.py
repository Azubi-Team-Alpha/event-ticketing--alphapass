"""
Notification Service — AlphaPass

Architecture:
  Lambda ──▶ publish_sns_notification() ──▶ Amazon SNS Topic ──▶ Email Subscribers

100% AWS SNS Driven Architecture:
  All platform notifications (booking confirmations, ticket transfers, order cancellations,
  resale alerts, and auth tokens) are published directly to the Amazon SNS Topic
  provisioned in infra/modules/sns/main.tf. This removes any dependency on AWS SES sandbox
  limits or domain verification.
"""
import html
import logging
import re
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── SNS NOTIFICATION ENGINE (100% EXCLUSIVE) ──────────────────────────────────

def publish_sns_notification(
    subject: str,
    message: str,
    topic_arn: Optional[str] = None,
) -> bool:
    """
    Publish a notification to the AWS SNS Confirmations Topic.

    The SNS topic delivers notifications to all email subscribers
    configured in infra/modules/sns/main.tf.

    Returns True on success, False on failure.
    """
    arn = topic_arn or settings.sns_arn
    if not arn:
        logger.warning(
            "[SNS] No SNS_TOPIC_ARN / CONFIRMATION_TOPIC configured — "
            "skipping SNS publish."
        )
        return False

    sns = boto3.client("sns", region_name=settings.AWS_REGION)
    try:
        clean_subject = subject[:100]
        response = sns.publish(
            TopicArn=arn,
            Subject=clean_subject,
            Message=message,
        )
        msg_id = response.get("MessageId")
        logger.info(f"[SNS] Published notification {msg_id!r} to {arn}: {clean_subject!r}")
        print(f"[SNS SUCCESS] Published notification {msg_id} to {arn}")
        return True
    except ClientError as e:
        logger.error(f"[SNS] ClientError publishing to {arn}: {e}")
        return False
    except Exception as e:
        logger.error(f"[SNS] Unexpected error publishing to {arn}: {e}")
        return False


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """
    Send notification via AWS SNS.
    Converts HTML content to readable plain text and publishes to the SNS Topic.
    """
    clean_text = re.sub(r'<br\s*/?>', '\n', html_body)
    clean_text = re.sub(r'</p>', '\n\n', clean_text)
    clean_text = re.sub(r'<[^>]+>', '', clean_text)
    clean_text = html.unescape(clean_text).strip()

    sns_message = f"Target Recipient: {to_email}\nSubject: {subject}\n\n{clean_text}"
    return publish_sns_notification(subject, sns_message)


# ── TICKET CONFIRMATION (100% SNS) ───────────────────────────────────────────

def send_ticket_confirmation(
    guest_email: str,
    guest_name: str,
    event: Dict[str, Any],
    order: Dict[str, Any],
    tickets: List[Dict[str, Any]],
) -> bool:
    """
    Send a booking confirmation notification via AWS SNS.
    """
    raw_title    = _raw(event, "title", "Event")
    raw_venue    = _raw(event, "venue_name", "TBD")
    raw_starts   = _raw(event, "starts_at", "TBD")
    raw_order_id = str(order.get("OrderID") or order.get("id", ""))
    raw_total    = str(order.get("total_amount", "0.00"))

    lines = [
        "🎉 AlphaPass — Booking Confirmed",
        "",
        f"Hi {guest_name},",
        f"Your order for \"{raw_title}\" has been confirmed.",
        "",
        "Order Summary:",
        f"  Order ID  : {raw_order_id}",
        f"  Event     : {raw_title}",
        f"  Date      : {raw_starts}",
        f"  Venue     : {raw_venue}",
        f"  Total Paid: ₵{raw_total}",
        f"  Buyer     : {guest_name} <{guest_email}>",
        "",
        f"Tickets Issued ({len(tickets)}):",
    ]

    for t in tickets:
        attendee = _raw(t, "attendee_name", guest_name)
        code     = _raw(t, "ticket_code", "")
        tt_name  = _raw(t, "ticket_type_name", "")
        lines.append(f"  • Code: {code} | Attendee: {attendee} | Type: {tt_name}")

    lines += [
        "",
        "Access your digital pass wallet at:",
        f"  {settings.FRONTEND_URL}/wallet.html",
        "",
        "— AlphaPass Serverless Platform",
    ]

    sns_message = "\n".join(lines)
    sns_subject = f"AlphaPass Order Confirmed: {raw_title} ({raw_order_id})"

    return publish_sns_notification(sns_subject, sns_message)


# ── TRANSFER NOTIFICATION (100% SNS) ─────────────────────────────────────────

def send_transfer_notification(
    from_email: str,
    from_name: str,
    to_email: str,
    to_name: str,
    event_title: str,
    ticket_code: str,
) -> bool:
    """
    Notify both parties of a ticket transfer via AWS SNS.
    """
    sns_message = "\n".join([
        "🔄 AlphaPass — Ticket Transferred",
        "",
        f"Ticket Code: {ticket_code}",
        f"Event      : {event_title}",
        f"Transferred From: {from_name} <{from_email}>",
        f"Transferred To  : {to_name} <{to_email}>",
        "",
        "The new holder can access their digital ticket at:",
        f"  {settings.FRONTEND_URL}/wallet.html",
        "",
        "— AlphaPass Serverless Platform",
    ])
    return publish_sns_notification(
        f"AlphaPass Ticket Transferred: {event_title}",
        sns_message,
    )


# ── HELPERS ────────────────────────────────────────────────────────────────────

def _h(value: Any) -> str:
    """HTML-escape a value."""
    return html.escape(str(value)) if value is not None else ""


def _raw(obj: Any, key: str, default: str = "") -> str:
    """Extract a raw string from a dict or object, falling back to default."""
    if isinstance(obj, dict):
        return str(obj.get(key) or default)
    return str(getattr(obj, key, default) or default)
