import io
from datetime import datetime, timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from app.core.qr import generate_qr_code


def generate_ticket_pdf(ticket) -> bytes:
    buffer = io.BytesIO()

    # 1. Setup document (Margins: 0.5 inch / 36 pt)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    ticket_code = getattr(ticket, "ticket_code", None) or (ticket.get("ticket_code") if isinstance(ticket, dict) else "TICKET")
    attendee_name = getattr(ticket, "attendee_name", None) or (ticket.get("attendee_name") if isinstance(ticket, dict) else "Guest")

    # Extract event data
    event = getattr(ticket, "event", None) or (ticket.get("event") if isinstance(ticket, dict) else None)
    if isinstance(event, dict):
        event_title = event.get("title", "Special Event")
        venue = event.get("venue_name", "TBD")
        address = event.get("address", "")
        city_country = f"{event.get('city') or ''}, {event.get('country') or ''}".strip(", ")
        policies = event.get("policies", "")
        starts_val = event.get("starts_at")
        ends_val = event.get("ends_at")
    elif event:
        event_title = getattr(event, "title", "Special Event")
        venue = getattr(event, "venue_name", "TBD")
        address = getattr(event, "address", "")
        city = getattr(event, "city", "")
        country = getattr(event, "country", "")
        city_country = f"{city or ''}, {country or ''}".strip(", ")
        policies = getattr(event, "policies", "")
        starts_val = getattr(event, "starts_at", None)
        ends_val = getattr(event, "ends_at", None)
    else:
        event_title = "Special Event"
        venue = "TBD"
        address = ""
        city_country = ""
        policies = ""
        starts_val = None
        ends_val = None

    # Dates
    def _parse_dt(val):
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

    dt_start = _parse_dt(starts_val)
    dt_end = _parse_dt(ends_val)
    starts_at = dt_start.strftime('%A, %B %d, %Y at %I:%M %p') if dt_start else "TBD"
    ends_at = dt_end.strftime('%I:%M %p') if dt_end else "TBD"
    date_str = f"{starts_at} - {ends_at}" if dt_end else starts_at

    location_str = f"{venue}\n{address}\n{city_country}".strip()

    # Ticket type
    tt = getattr(ticket, "ticket_type", None) or (ticket.get("ticket_type") if isinstance(ticket, dict) else None)
    if isinstance(tt, dict):
        ticket_type_name = tt.get("name", "General Admission")
        price_str = f"${tt.get('price', '0.00')}"
    elif tt:
        ticket_type_name = getattr(tt, "name", "General Admission")
        price = getattr(tt, "price", "0.00")
        price_str = f"${price}"
    else:
        ticket_type_name = ticket.get("ticket_type_name", "General Admission") if isinstance(ticket, dict) else "General Admission"
        price_str = "$0.00"

    # 2. Get QR image wrap
    qr_bytes = generate_qr_code(ticket_code)
    qr_image = Image(io.BytesIO(qr_bytes), width=1.5 * inch, height=1.5 * inch)

    # 3. Create Styles
    styles = getSampleStyleSheet()

    primary_color = colors.HexColor("#6366f1")    # Indigo
    dark_text = colors.HexColor("#1e293b")        # Slate-800
    light_bg = colors.HexColor("#f8fafc")         # Slate-50
    border_color = colors.HexColor("#e2e8f0")     # Slate-200
    gray_text = colors.HexColor("#64748b")        # Slate-500

    title_style = ParagraphStyle(
        'TicketTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.white,
        spaceAfter=10
    )

    subtitle_style = ParagraphStyle(
        'TicketSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=12,
        textColor=colors.white
    )

    event_title_style = ParagraphStyle(
        'EventTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=primary_color,
        spaceAfter=12
    )

    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=gray_text
    )

    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=dark_text
    )

    code_label_style = ParagraphStyle(
        'CodeLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=gray_text,
        alignment=1
    )

    code_val_style = ParagraphStyle(
        'CodeValue',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=9,
        leading=11,
        textColor=dark_text,
        alignment=1
    )

    story = []

    # ── HEADER CARD ──
    header_data = [
        [
            Paragraph("ALPHAPASS", title_style),
            Paragraph(f"TICKET #{ticket_code[:8].upper()}", ParagraphStyle('RightHeader', parent=title_style, alignment=2))
        ],
        [
            Paragraph("Official Event Ticket", subtitle_style),
            Paragraph("Guest-First Checkout", ParagraphStyle('RightSub', parent=subtitle_style, alignment=2))
        ]
    ]

    header_table = Table(header_data, colWidths=[4.0 * inch, 3.5 * inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), primary_color),
        ('PADDING', (0, 0), (-1, -1), 16),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 15))

    # ── CONTENT TABLE ──
    left_flow = [
        Paragraph(event_title, event_title_style),
        Paragraph("DATE & TIME", label_style),
        Paragraph(date_str, value_style),
        Spacer(1, 8),
        Paragraph("LOCATION", label_style),
        Paragraph(location_str.replace('\n', '<br/>'), value_style),
        Spacer(1, 12),

        Table([
            [Paragraph("ATTENDEE", label_style), Paragraph("TICKET TYPE", label_style), Paragraph("PRICE", label_style)],
            [Paragraph(attendee_name, value_style), Paragraph(ticket_type_name, value_style), Paragraph(price_str, value_style)]
        ], colWidths=[2.2 * inch, 1.8 * inch, 1.0 * inch], style=[
            ('PADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ])
    ]

    right_flow = [
        qr_image,
        Spacer(1, 6),
        Paragraph("TICKET CODE", code_label_style),
        Paragraph(ticket_code, code_val_style)
    ]

    main_table = Table([[left_flow, right_flow]], colWidths=[5.3 * inch, 2.2 * inch])
    main_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_bg),
        ('PADDING', (0, 0), (-1, -1), 16),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
    ]))
    story.append(main_table)
    story.append(Spacer(1, 20))

    terms_title_style = ParagraphStyle(
        'TermsTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=dark_text,
        spaceAfter=6
    )
    terms_body_style = ParagraphStyle(
        'TermsBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=gray_text
    )

    story.append(Paragraph("IMPORTANT INFORMATION", terms_title_style))
    story.append(Paragraph(
        "• Please present this ticket at the venue entrance. The QR code must be clearly readable on a phone screen or printed paper.<br/>"
        "• Each ticket is valid for one (1) entry and can only be scanned once. Duplicate scans will be rejected.<br/>"
        "• Admission policies (age restrictions, dress code, etc.) are set by the organizer. Event policies: "
        f"<i>{policies or 'Standard platform terms apply.'}</i><br/>"
        "• Keep this ticket secure. Do not share the QR code or link to prevent unauthorized transfers.",
        terms_body_style
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
