"""
Notification Service — AlphaPass

Architecture (per docs/integration.md):
  Lambda ──▶ sns.publish() ──▶ SNS Topic ──▶ Email Subscription
                                          └──▶ (optional) SES direct-to-buyer

SNS is the PRIMARY path for all booking notifications.
SES is an OPTIONAL secondary path (only used when SES_SENDER_EMAIL is configured
in the Lambda environment) to send a rich HTML copy directly to the individual buyer.

This matches the architecture diagram:
  Lambda → "6. Publish Booking Alerts" → SNS
"""
import html
import logging
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── SNS (PRIMARY) ─────────────────────────────────────────────────────────────

def publish_sns_notification(
    subject: str,
    message: str,
    topic_arn: Optional[str] = None,
) -> bool:
    """
    Publish a notification to the AWS SNS Confirmations Topic.

    The SNS topic has an email subscription (provisioned by Terraform in
    infra/modules/sns/main.tf) that forwards messages to the configured
    notification_email address. This is the primary notification mechanism
    per the project architecture doc.

    Returns True on success, False on failure.
    """
    arn = topic_arn or settings.sns_arn
    if not arn:
        logger.warning(
            "[SNS] No SNS_TOPIC_ARN / CONFIRMATION_TOPIC configured — "
            "skipping SNS publish. Set the environment variable in Lambda."
        )
        return False

    sns = boto3.client("sns", region_name=settings.AWS_REGION)
    try:
        # SNS Subject max length is 100 chars
        clean_subject = subject[:100]
        response = sns.publish(
            TopicArn=arn,
            Subject=clean_subject,
            Message=message,
        )
        msg_id = response.get("MessageId")
        logger.info(f"[SNS] Published message {msg_id!r} to {arn}: {clean_subject!r}")
        return True
    except ClientError as e:
        logger.error(f"[SNS] ClientError publishing to {arn}: {e}")
        return False
    except Exception as e:
        logger.error(f"[SNS] Unexpected error publishing to {arn}: {e}")
        return False


# ── SES (OPTIONAL SECONDARY) ───────────────────────────────────────────────────

def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """
    Send an HTML email directly to an individual recipient via AWS SES.

    This is SECONDARY to SNS. It is only attempted when SES_SENDER_EMAIL
    is configured. If SES is not configured or is in sandbox mode this
    function logs a warning and returns False — it never raises.
    """
    sender = settings.SES_SENDER_EMAIL
    if not sender or sender == "noreply@alphapass.alphateam.live":
        # Attempt anyway; SES will log error if not verified.
        pass

    ses = boto3.client("ses", region_name=settings.AWS_REGION)
    try:
        ses.send_email(
            Source=sender,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": _wrap_html(html_body), "Charset": "UTF-8"}},
            },
        )
        logger.info(f"[SES] Email sent to {to_email}: {subject!r}")
        return True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "MessageRejected":
            logger.warning(
                f"[SES] MessageRejected for {to_email}. "
                "If using SES sandbox, the recipient must be verified. "
                f"Error: {e}"
            )
        elif code == "EmailAddressNotVerified":
            logger.warning(
                f"[SES] Unverified sender {sender!r}. "
                "Verify the sender address in AWS SES console or request production access."
            )
        else:
            logger.error(f"[SES] Failed to send to {to_email}: {e}")
        return False
    except Exception as e:
        logger.error(f"[SES] Unexpected error sending to {to_email}: {e}")
        return False


# ── TICKET CONFIRMATION (SNS-first) ───────────────────────────────────────────

def send_ticket_confirmation(
    guest_email: str,
    guest_name: str,
    event: Dict[str, Any],
    order: Dict[str, Any],
    tickets: List[Dict[str, Any]],
) -> bool:
    """
    Send a booking confirmation notification.

    Flow (per docs/integration.md architecture):
      1. Publish to SNS Topic (primary — always attempted).
         The SNS topic's email subscription delivers this to the platform
         notification address (set via notification_email Terraform variable).
      2. Send rich HTML copy to the individual buyer via SES (secondary —
         only attempted if SES_SENDER_EMAIL is set as a Lambda env var).

    Returns True if at least one delivery path succeeded.
    """
    # ── Extract and HTML-escape all user-supplied values ──────────────────────
    raw_title  = _raw(event, "title", "Event")
    raw_venue  = _raw(event, "venue_name", "TBD")
    raw_starts = _raw(event, "starts_at", "TBD")
    raw_order_id = str(order.get("OrderID") or order.get("id", ""))
    raw_total    = str(order.get("total_amount", "0.00"))

    safe_title    = _h(raw_title)
    safe_venue    = _h(raw_venue)
    safe_starts   = _h(raw_starts)
    safe_order_id = _h(raw_order_id)
    safe_total    = _h(raw_total)
    safe_name     = _h(guest_name)
    safe_email    = _h(guest_email)

    # ── 1. Build plain-text SNS message ───────────────────────────────────────
    lines = [
        "🎉 AlphaPass — Booking Confirmed",
        "",
        f"Hi {guest_name},",
        f"Your order for \"{raw_title}\" has been confirmed.",
        "",
        "Order Summary",
        f"  Order ID  : {raw_order_id}",
        f"  Event     : {raw_title}",
        f"  Date      : {raw_starts}",
        f"  Venue     : {raw_venue}",
        f"  Total Paid: ₵{raw_total}",
        f"  Buyer     : {guest_name} <{guest_email}>",
        "",
        f"Tickets Issued ({len(tickets)}):",
    ]

    ticket_rows_html = ""
    for t in tickets:
        attendee = _raw(t, "attendee_name", guest_name)
        code     = _raw(t, "ticket_code", "")
        tt_name  = _raw(t, "ticket_type_name", "")
        lines.append(f"  • {_h(code)}  |  {_h(attendee)}  |  {_h(tt_name)}")
        ticket_rows_html += (
            f"<tr>"
            f"<td>{_h(attendee)}</td>"
            f"<td><code>{_h(code)}</code></td>"
            f"<td>{_h(tt_name)}</td>"
            f"</tr>"
        )

    lines += [
        "",
        "Access your digital pass at:",
        "  https://alphapass.alphateam.live/wallet.html",
        "",
        "— AlphaPass Platform",
    ]

    sns_message = "\n".join(lines)
    sns_subject = f"AlphaPass Order Confirmed: {raw_title} ({raw_order_id})"

    # Publish to SNS (primary path)
    sns_ok = publish_sns_notification(sns_subject, sns_message)

    # ── 2. Send rich HTML copy to buyer via SES (secondary path) ─────────────
    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;">
      <h2 style="color:#6366f1;">You're going! 🎉</h2>
      <p>Hi <strong>{safe_name}</strong>,</p>
      <p>Your order for <strong>{safe_title}</strong> is confirmed.</p>
      <div style="background:#f4f5f7;padding:16px;border-radius:8px;margin:20px 0;">
        <p><strong>📅 Date:</strong> {safe_starts}</p>
        <p><strong>📍 Venue:</strong> {safe_venue}</p>
        <p><strong>🎟 Order:</strong> {safe_order_id}</p>
        <p><strong>💰 Total:</strong> ₵{safe_total}</p>
      </div>
      <h3>Your Tickets</h3>
      <table border="1" cellpadding="8" style="border-collapse:collapse;width:100%;">
        <tr><th>Attendee</th><th>Ticket Code</th><th>Type</th></tr>
        {ticket_rows_html}
      </table>
      <p style="margin-top:20px;">
        <a href="https://alphapass.alphateam.live/wallet.html"
           style="background:#6366f1;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;">
          View My Tickets →
        </a>
      </p>
      <p style="color:#5E6C84;font-size:12px;margin-top:20px;">
        Show your ticket code at the entrance. Sent by AlphaPass.
      </p>
    </div>
    """
    ses_ok = send_email(guest_email, f"Your tickets for {raw_title} 🎟", html_body)

    return sns_ok or ses_ok


# ── TRANSFER NOTIFICATION (SNS-first) ─────────────────────────────────────────

def send_transfer_notification(
    from_email: str,
    from_name: str,
    to_email: str,
    to_name: str,
    event_title: str,
    ticket_code: str,
) -> bool:
    """
    Notify both parties of a ticket transfer via SNS (primary) + SES (secondary).
    """
    safe_from  = _h(from_name)
    safe_to    = _h(to_name)
    safe_to_e  = _h(to_email)
    safe_event = _h(event_title)
    safe_code  = _h(ticket_code)

    sns_message = "\n".join([
        "🔄 AlphaPass — Ticket Transferred",
        "",
        f"Ticket: {ticket_code}",
        f"Event : {event_title}",
        f"From  : {from_name} <{from_email}>",
        f"To    : {to_name} <{to_email}>",
        "",
        "The new holder can access their ticket at:",
        "  https://alphapass.alphateam.live/wallet.html",
    ])
    sns_ok = publish_sns_notification(
        f"AlphaPass Ticket Transferred: {event_title}",
        sns_message,
    )

    # SES secondary — notify sender
    ses_from_ok = send_email(
        from_email,
        f"Ticket Transferred – {event_title}",
        f"<p>Hi {safe_from}, your ticket <code>{safe_code}</code> for "
        f"<strong>{safe_event}</strong> has been transferred to "
        f"{safe_to} ({safe_to_e}).</p>",
    )
    # SES secondary — notify recipient
    ses_to_ok = send_email(
        to_email,
        f"You received a ticket – {event_title}",
        f"<p>Hi {safe_to}, you received a ticket for <strong>{safe_event}</strong>. "
        f"Ticket code: <code>{safe_code}</code></p>",
    )

    return sns_ok or ses_from_ok or ses_to_ok


# ── HELPERS ────────────────────────────────────────────────────────────────────

def _h(value: Any) -> str:
    """HTML-escape a value."""
    return html.escape(str(value)) if value is not None else ""


def _raw(obj: Any, key: str, default: str = "") -> str:
    """Extract a raw string from a dict or object, falling back to default."""
    if isinstance(obj, dict):
        return str(obj.get(key) or default)
    return str(getattr(obj, key, default) or default)


def _wrap_html(body: str) -> str:
    sender = html.escape(settings.SES_SENDER_EMAIL)
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>body{{font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;color:#1a1a1a;}}</style>
</head><body>{body}<hr style="margin-top:40px;">
<p style="color:#999;font-size:11px;">AlphaPass &mdash; {sender}</p>
</body></html>"""
