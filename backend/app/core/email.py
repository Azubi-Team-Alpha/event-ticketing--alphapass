"""Email and Notification Service using AWS SNS & AWS SES with HTML-safe templating."""
import html
import logging
from typing import Any, Optional, Dict, List
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings

logger = logging.getLogger(__name__)


def publish_sns_notification(subject: str, message: str, topic_arn: Optional[str] = None) -> bool:
    """
    Publish a notification message to an AWS SNS Topic.
    Uses settings.sns_arn if topic_arn is not specified.
    Returns True on success, False on failure.
    """
    arn = topic_arn or settings.sns_arn
    if not arn:
        logger.info("[SNS] Skipping SNS publish: No SNS_TOPIC_ARN or CONFIRMATION_TOPIC configured.")
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
        logger.info(f"[SNS] Published message {msg_id} to topic {arn}: {clean_subject!r}")
        return True
    except ClientError as e:
        logger.error(f"[SNS] ClientError publishing to {arn}: {e}")
        return False
    except Exception as e:
        logger.error(f"[SNS] Unexpected error publishing to {arn}: {e}")
        return False


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """
    Send a single HTML email via AWS SES.

    Returns True on success, False on failure.
    Errors are logged but never raised so that delivery failure does not
    abort the calling request.
    """
    ses = boto3.client("ses", region_name=settings.AWS_REGION)
    try:
        ses.send_email(
            Source=settings.SES_SENDER_EMAIL,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": _wrap_html(html_body), "Charset": "UTF-8"}},
            },
        )
        logger.info(f"[SES] Email sent to {to_email}: {subject!r}")
        return True
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "MessageRejected":
            logger.warning(
                f"[SES] MessageRejected for {to_email}. "
                "If using SES sandbox, the recipient address must be verified. "
                f"Error: {e}"
            )
        elif error_code == "EmailAddressNotVerified":
            logger.warning(
                f"[SES] Unverified sender {settings.SES_SENDER_EMAIL!r}. "
                "Verify the sender address in AWS SES console."
            )
        else:
            logger.error(f"[SES] Failed to send email to {to_email}: {e}")
        return False
    except Exception as e:
        logger.error(f"[SES] Unexpected error sending to {to_email}: {e}")
        return False


def send_ticket_confirmation(guest_email: str, guest_name: str, event: Dict[str, Any], order: Dict[str, Any], tickets: List[Dict[str, Any]]) -> bool:
    """
    Sends a ticket confirmation notification via AWS SNS and AWS SES after a successful booking.
    """
    # Safely extract event/order data
    raw_event_title = event.get("title") if isinstance(event, dict) else getattr(event, "title", "Event")
    event_title = _h(raw_event_title)
    event_starts = _h(str(event.get("starts_at") if isinstance(event, dict) else getattr(event, "starts_at", "TBD")))
    event_venue = _h(str(event.get("venue_name") if isinstance(event, dict) else getattr(event, "venue_name", "TBD") or "TBD"))
    order_id = _h(str(order.get("OrderID") or order.get("id", "")))
    total_amount = _h(str(order.get("total_amount", "0.00")))
    safe_name = _h(guest_name)

    # 1. Format plain-text message for AWS SNS topic notification
    sns_lines = [
      f"🎉 AlphaPass Ticket Confirmation",
      f"Hi {guest_name},",
      f"Your order for {raw_event_title} has been confirmed!",
      f"",
      f"Order Summary:",
      f"• Order ID: {order_id}",
      f"• Date: {event_starts}",
      f"• Venue: {event_venue}",
      f"• Total Paid: ₵{total_amount}",
      f"• Guest Email: {guest_email}",
      f"",
      f"Tickets Issued ({len(tickets)}):"
    ]

    ticket_rows_html = ""
    for t in tickets:
        attendee = _h(str(t.get("attendee_name") if isinstance(t, dict) else getattr(t, "attendee_name", guest_name) or guest_name))
        code = _h(str(t.get("ticket_code") if isinstance(t, dict) else getattr(t, "ticket_code", "")))
        tt_name = _h(str(t.get("ticket_type_name", "") or ""))
        ticket_rows_html += f"<tr><td>{attendee}</td><td><code>{code}</code></td><td>{tt_name}</td></tr>"
        sns_lines.append(f"  - Ticket Pass: {code} | Attendee: {attendee} | Tier: {tt_name}")

    sns_lines.append("")
    sns_lines.append("Access your digital pass and QR code anytime at: https://alphapass.alphateam.live/wallet.html")

    sns_message = "\n".join(sns_lines)
    sns_subject = f"AlphaPass Order Confirmed: {raw_event_title} ({order_id})"

    # Publish to AWS SNS Topic
    sns_published = publish_sns_notification(sns_subject, sns_message)

    # 2. Build HTML body for AWS SES direct recipient delivery
    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;">
      <h2 style="color:#6366f1;">You're going! 🎉</h2>
      <p>Hi <strong>{safe_name}</strong>,</p>
      <p>Your order for <strong>{event_title}</strong> is confirmed.</p>
      <div style="background:#f4f5f7;padding:16px;border-radius:8px;margin:20px 0;">
        <p><strong>📅 Date:</strong> {event_starts}</p>
        <p><strong>📍 Venue:</strong> {event_venue}</p>
        <p><strong>🎟 Order:</strong> {order_id}</p>
        <p><strong>💰 Total:</strong> ₵{total_amount}</p>
      </div>
      <h3>Your Tickets</h3>
      <table border="1" cellpadding="8" style="border-collapse:collapse;width:100%;">
        <tr><th>Attendee</th><th>Ticket Code</th><th>Type</th></tr>
        {ticket_rows_html}
      </table>
      <p style="color:#5E6C84;font-size:12px;margin-top:20px;">
        Show your QR code or ticket code at the entrance. Sent by AlphaPass.
      </p>
    </div>
    """
    ses_sent = send_email(guest_email, f"Your tickets for {raw_event_title} 🎟", html_body)

    return sns_published or ses_sent


def _h(value: Any) -> str:
    """HTML-escape a value to prevent injection in email templates."""
    return html.escape(str(value)) if value is not None else ""


def _wrap_html(body: str) -> str:
    sender = html.escape(settings.SES_SENDER_EMAIL)
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>body{{font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;color:#1a1a1a;}}</style>
</head><body>{body}<hr style="margin-top:40px;">
<p style="color:#999;font-size:11px;">AlphaPass &mdash; {sender}</p>
</body></html>"""
