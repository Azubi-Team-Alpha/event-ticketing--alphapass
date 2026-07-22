"""Email service using AWS SES."""
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings


def send_email(to_email: str, subject: str, html_body: str):
    """Send a single HTML email via AWS SES."""
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
    except ClientError as e:
        print(f"[SES ERROR] Failed to send email to {to_email}: {e}")
        # Note: Do not crash production flow on email delivery failure if SES is in sandbox
        pass


def send_ticket_confirmation(guest_email, guest_name, event, order, tickets):
    """
    Sends a ticket confirmation email with all ticket codes after a successful order.
    """
    event_title = event.get("title") if isinstance(event, dict) else getattr(event, "title", "Event")
    event_starts = event.get("starts_at") if isinstance(event, dict) else getattr(event, "starts_at", "TBD")
    event_venue = event.get("venue_name") if isinstance(event, dict) else getattr(event, "venue_name", "TBD")
    order_id = order.get("OrderID") if isinstance(order, dict) else getattr(order, "id", "")
    total_amount = order.get("total_amount") if isinstance(order, dict) else getattr(order, "total_amount", "0.00")

    ticket_rows_list = []
    for t in tickets:
        attendee = t.get("attendee_name") if isinstance(t, dict) else getattr(t, "attendee_name", guest_name)
        code = t.get("ticket_code") if isinstance(t, dict) else getattr(t, "ticket_code", "")
        tt_name = t.get("ticket_type_name", "")
        ticket_rows_list.append(f"<tr><td>{attendee or guest_name}</td><td><code>{code}</code></td><td>{tt_name}</td></tr>")

    ticket_rows = "".join(ticket_rows_list)
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;">
      <h2 style="color:#6366f1;">You're going! 🎉</h2>
      <p>Hi <strong>{guest_name}</strong>,</p>
      <p>Your order for <strong>{event_title}</strong> is confirmed.</p>
      <div style="background:#f4f5f7;padding:16px;border-radius:8px;margin:20px 0;">
        <p><strong>📅 Date:</strong> {event_starts}</p>
        <p><strong>📍 Venue:</strong> {event_venue or 'TBD'}</p>
        <p><strong>🎟 Order:</strong> {order_id}</p>
        <p><strong>💰 Total:</strong> ${total_amount}</p>
      </div>
      <h3>Your Tickets</h3>
      <table border="1" cellpadding="8" style="border-collapse:collapse;width:100%;">
        <tr><th>Attendee</th><th>Ticket Code</th><th>Type</th></tr>
        {ticket_rows}
      </table>
      <p style="color:#5E6C84;font-size:12px;margin-top:20px;">
        Show your QR code at the entrance. Sent by AlphaPass.
      </p>
    </div>
    """
    send_email(guest_email, f"Your tickets for {event_title} 🎟", html)


def _wrap_html(body: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>body{{font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;color:#1a1a1a;}}</style>
</head><body>{body}<hr style="margin-top:40px;">
<p style="color:#999;font-size:11px;">AlphaPass &mdash; {settings.SES_SENDER_EMAIL}</p>
</body></html>"""
