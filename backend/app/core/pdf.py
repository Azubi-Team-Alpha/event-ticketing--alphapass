import io
import html
from datetime import datetime, timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


def generate_ticket_pdf(ticket) -> bytes:
    buffer = io.BytesIO()

    # Setup document (Margins: 0.5 inch / 36 pt)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    ticket_code = str(getattr(ticket, "ticket_code", None) or (ticket.get("ticket_code") if isinstance(ticket, dict) else "") or "TICKET")
    attendee_name = str(getattr(ticket, "attendee_name", None) or (ticket.get("attendee_name") if isinstance(ticket, dict) else "") or "Guest Attendee")

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

    # Ticket type & pricing
    tt = getattr(ticket, "ticket_type", None) or (ticket.get("ticket_type") if isinstance(ticket, dict) else None)
    if isinstance(tt, dict):
        ticket_type_name = tt.get("name", "General Admission")
        price_str = f"₵{tt.get('price', '0.00')}"
    elif tt:
        ticket_type_name = getattr(tt, "name", "General Admission")
        price = getattr(tt, "price", "0.00")
        price_str = f"₵{price}"
    else:
        ticket_type_name = str(getattr(ticket, "ticket_type_name", None) or (ticket.get("ticket_type") if isinstance(ticket, dict) else "") or "General Pass")
        price_str = "₵0.00"

    # HTML Escape all dynamic values for ReportLab Paragraph compatibility
    event_title_esc = html.escape(str(event_title))
    attendee_name_esc = html.escape(str(attendee_name))
    ticket_type_name_esc = html.escape(str(ticket_type_name))
    date_str_esc = html.escape(str(date_str))
    location_str_esc = html.escape(str(location_str)).replace('\n', '<br/>')
    policies_esc = html.escape(str(policies)) if policies else "Standard platform terms apply."

    # Create Styles
    styles = getSampleStyleSheet()

    primary_color = colors.HexColor("#4f46e5")    # Indigo
    dark_text = colors.HexColor("#1e293b")        # Slate-800
    light_bg = colors.HexColor("#f8fafc")         # Slate-50
    border_color = colors.HexColor("#cbd5e1")     # Slate-300
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
        fontSize=9,
        leading=11,
        textColor=gray_text,
        alignment=1
    )

    code_val_style = ParagraphStyle(
        'CodeValue',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=13,
        leading=15,
        textColor=primary_color,
        alignment=1
    )

    story = []

    # ── HEADER CARD ──
    header_data = [
        [
            Paragraph("ALPHAPASS", title_style),
            Paragraph(f"TICKET #{html.escape(ticket_code[:12].upper())}", ParagraphStyle('RightHeader', parent=title_style, alignment=2))
        ],
        [
            Paragraph("Official Event Entry Pass", subtitle_style),
            Paragraph("Verified Digital Ticket Pass", ParagraphStyle('RightSub', parent=subtitle_style, alignment=2))
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

    # ── CONTENT TABLE WITH QR CODE MATRIX ──
    left_flow = [
        Paragraph(event_title_esc, event_title_style),
        Paragraph("DATE & TIME", label_style),
        Paragraph(date_str_esc, value_style),
        Spacer(1, 8),
        Paragraph("LOCATION", label_style),
        Paragraph(location_str_esc, value_style),
        Spacer(1, 12),

        Table([
            [Paragraph("ATTENDEE", label_style), Paragraph("TICKET TYPE", label_style), Paragraph("PRICE", label_style)],
            [Paragraph(attendee_name_esc, value_style), Paragraph(ticket_type_name_esc, value_style), Paragraph(html.escape(price_str), value_style)]
        ], colWidths=[2.2 * inch, 1.8 * inch, 1.0 * inch], style=[
            ('PADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ])
    ]

    # Generate QR Code Drawing for ReportLab
    try:
        from reportlab.graphics.barcode import qr
        from reportlab.graphics.shapes import Drawing
        qr_widget = qr.QrCodeWidget(ticket_code)
        b = qr_widget.getBounds()
        w = b[2] - b[0]
        h = b[3] - b[1]
        qr_drawing = Drawing(110, 110, transform=[110 / w, 0, 0, 110 / h, 0, 0])
        qr_drawing.add(qr_widget)
    except Exception:
        qr_drawing = Spacer(1, 10)

    right_flow = [
        Spacer(1, 5),
        qr_drawing,
        Spacer(1, 8),
        Paragraph("OFFICIAL TICKET CODE", code_label_style),
        Spacer(1, 4),
        Paragraph(html.escape(ticket_code), code_val_style),
        Spacer(1, 6),
        Paragraph("Scan QR code at venue gate", ParagraphStyle('CodeSub', parent=code_label_style, fontSize=8))
    ]

    main_table = Table([[left_flow, right_flow]], colWidths=[4.8 * inch, 2.7 * inch])
    main_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_bg),
        ('PADDING', (0, 0), (-1, -1), 16),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
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
        "• Please present your official ticket code or QR code at the venue entrance for gate check-in.<br/>"
        "• Each ticket pass code is valid for one (1) entry and can only be scanned once.<br/>"
        "• Admission policies are set by the organizer. Event policies: "
        f"<i>{policies_esc}</i><br/>"
        "• Keep this ticket pass secure and do not share your unique ticket code to prevent unauthorized entry.",
        terms_body_style
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_attendee_list_pdf(event_title: str, tickets: list) -> bytes:
    """Generate a printable PDF roster of event attendees matching CSV layout."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#4f46e5")
    dark_text = colors.HexColor("#1e293b")
    light_bg = colors.HexColor("#f8fafc")
    alt_bg = colors.HexColor("#f1f5f9")
    border_color = colors.HexColor("#cbd5e1")
    gray_text = colors.HexColor("#64748b")

    title_style = ParagraphStyle(
        'RosterTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=primary_color,
        spaceAfter=4
    )
    meta_style = ParagraphStyle(
        'RosterMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=gray_text,
        spaceAfter=14
    )

    header_cell_style = ParagraphStyle(
        'HeaderCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )
    cell_style = ParagraphStyle(
        'DataCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=dark_text
    )

    story = []
    event_title_esc = html.escape(str(event_title or "Event Attendees"))
    story.append(Paragraph(f"Attendee Roster - {event_title_esc}", title_style))
    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y %I:%M %p UTC")
    story.append(Paragraph(f"Generated on {now_str} | Total Attendees: {len(tickets)}", meta_style))

    table_data = [
        [
            Paragraph("Ticket Code", header_cell_style),
            Paragraph("Attendee Name", header_cell_style),
            Paragraph("Attendee Email", header_cell_style),
            Paragraph("Ticket Type", header_cell_style),
            Paragraph("Status", header_cell_style),
            Paragraph("Checked In", header_cell_style),
            Paragraph("Checked In At", header_cell_style),
        ]
    ]

    for t in tickets:
        t_code = html.escape(str(t.get("ticket_code") or ""))
        name = html.escape(str(t.get("attendee_name") or ""))
        email = html.escape(str(t.get("attendee_email") or ""))
        t_type = html.escape(str(t.get("ticket_type") or ""))
        status = html.escape(str(t.get("status") or ""))
        checked_in = "Yes" if t.get("checked_in") else "No"
        checked_at = html.escape(str(t.get("checked_in_at") or ""))

        table_data.append([
            Paragraph(t_code, cell_style),
            Paragraph(name, cell_style),
            Paragraph(email, cell_style),
            Paragraph(t_type, cell_style),
            Paragraph(status, cell_style),
            Paragraph(checked_in, cell_style),
            Paragraph(checked_at, cell_style),
        ])

    col_widths = [85, 95, 120, 80, 50, 50, 60]
    attendee_table = Table(table_data, colWidths=col_widths, repeatRows=1)

    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
    ]

    for i in range(1, len(table_data)):
        if i % 2 == 0:
            t_style.append(('BACKGROUND', (0, i), (-1, i), alt_bg))
        else:
            t_style.append(('BACKGROUND', (0, i), (-1, i), light_bg))

    attendee_table.setStyle(TableStyle(t_style))
    story.append(attendee_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
