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
        raise


def send_ticket_confirmation(guest_email, guest_name, event, order, tickets):
    """
    Sends a ticket confirmation email with all ticket codes after a successful order.
    Legacy helper – now superseded by the background task in orders.py,
    but kept for direct calls.
    """
    ticket_rows = "".join(
        f"<tr><td>{t.attendee_name or guest_name}</td>"
        f"<td><code>{t.ticket_code}</code></td>"
        f"<td>{t.order_item.ticket_type.name if t.order_item and t.order_item.ticket_type else ''}</td></tr>"
        for t in tickets
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;">
      <h2 style="color:#6366f1;">You're going! 🎉</h2>
      <p>Hi <strong>{guest_name}</strong>,</p>
      <p>Your order for <strong>{event.title}</strong> is confirmed.</p>
      <div style="background:#f4f5f7;padding:16px;border-radius:8px;margin:20px 0;">
        <p><strong>📅 Date:</strong> {event.starts_at.strftime('%A, %B %d %Y at %H:%M')}</p>
        <p><strong>📍 Venue:</strong> {event.venue_name or 'TBD'}</p>
        <p><strong>🎟 Order:</strong> {order.id}</p>
        <p><strong>💰 Total:</strong> ${order.total_amount}</p>
      </div>
      <h3>Your Tickets</h3>
      <table border="1" cellpadding="8" style="border-collapse:collapse;width:100%;">
        <tr><th>Attendee</th><th>Ticket Code</th><th>Type</th></tr>
        {ticket_rows}
      </table>
      <p style="color:#5E6C84;font-size:12px;margin-top:20px;">
        Show your QR code at the entrance. Sent by Ticket Hub.
      </p>
    </div>
    """
    send_email(guest_email, f"Your tickets for {event.title} 🎟", html)


def _wrap_html(body: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>body{{font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;color:#1a1a1a;}}</style>
</head><body>{body}<hr style="margin-top:40px;">
<p style="color:#999;font-size:11px;">Ticket Hub &mdash; {settings.SES_SENDER_EMAIL}</p>
</body></html>"""
