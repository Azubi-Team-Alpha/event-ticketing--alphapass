"""Email service using AWS SES with HTML-safe templating."""
import html
import logging
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings

logger = logging.getLogger(__name__)


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


def send_ticket_confirmation(guest_email: str, guest_name: str, event: dict, order: dict, tickets: list) -> bool:
    """
    Sends a ticket confirmation email with all ticket codes after a successful order.

    All user-controlled values are HTML-escaped before insertion.
    """
    # Safely extract event/order data
    event_title = _h(event.get("title") if isinstance(event, dict) else getattr(event, "title", "Event"))
    event_starts = _h(str(event.get("starts_at") if isinstance(event, dict) else getattr(event, "starts_at", "TBD")))
    event_venue = _h(str(event.get("venue_name") if isinstance(event, dict) else getattr(event, "venue_name", "TBD") or "TBD"))
    order_id = _h(str(order.get("OrderID") if isinstance(order, dict) else getattr(order, "id", "")))
    total_amount = _h(str(order.get("total_amount") if isinstance(order, dict) else getattr(order, "total_amount", "0.00")))
    safe_name = _h(guest_name)

    ticket_rows_html = ""
    for t in tickets:
        attendee = _h(str(t.get("attendee_name") if isinstance(t, dict) else getattr(t, "attendee_name", guest_name) or guest_name))
        code = _h(str(t.get("ticket_code") if isinstance(t, dict) else getattr(t, "ticket_code", "")))
        tt_name = _h(str(t.get("ticket_type_name", "") or ""))
        ticket_rows_html += f"<tr><td>{attendee}</td><td><code>{code}</code></td><td>{tt_name}</td></tr>"

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
    return send_email(guest_email, f"Your tickets for {event.get('title', 'AlphaPass')} 🎟", html_body)


def _h(value: str) -> str:
    """HTML-escape a string to prevent injection in email templates."""
    return html.escape(str(value))


def _wrap_html(body: str) -> str:
    sender = html.escape(str(settings.SES_SENDER_EMAIL))
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>body{{font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;color:#1a1a1a;}}</style>
</head><body>{body}<hr style="margin-top:40px;">
<p style="color:#999;font-size:11px;">AlphaPass &mdash; {sender}</p>
</body></html>"""
