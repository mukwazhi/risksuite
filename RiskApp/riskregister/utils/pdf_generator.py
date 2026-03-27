import os
from datetime import datetime
from io import BytesIO
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, PageBreak, Image
)
from reportlab.pdfgen import canvas
from django.db.models import Q

from ..models import ActivityLog


class NumberedCanvas(canvas.Canvas):
    """Custom canvas to add page numbers"""
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        canvas.Canvas.showPage(self)

    def save(self):
        """Add page numbers to each page"""
        num_pages = len(self._saved_page_states)
        for page_num in range(num_pages):
            self.__dict__.update(self._saved_page_states[page_num])
            self.draw_page_number(page_num + 1, num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_number, page_count):
        """Draw page number at bottom of page"""
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.grey)
        page_num = f"Page {page_number} of {page_count}"
        self.drawRightString(
            landscape(A4)[0] - 0.75 * inch,
            0.5 * inch,
            page_num
        )
        # Add generation timestamp
        timestamp = f"Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        self.drawString(0.75 * inch, 0.5 * inch, timestamp)


def wrap_text(text, max_length=60):
    """Wrap text to prevent overflow in PDF cells"""
    if not text:
        return ""
    text = str(text)
    if len(text) <= max_length:
        return text
    
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= max_length:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return '\n'.join(lines)


def generate_risk_report_pdf(risks_queryset, filters_applied=None):
    """
    Generate a comprehensive PDF report for risks.
    
    Args:
        risks_queryset: Django queryset of Risk objects
        filters_applied: Dictionary of filters applied (optional, for display)
    
    Returns:
        tuple: (file_path, filename) of the generated PDF
    """
    # Create media directory if it doesn't exist
    media_root = settings.MEDIA_ROOT
    reports_dir = os.path.join(media_root, 'risk_reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'risk_report_{timestamp}.pdf'
    filepath = os.path.join(reports_dir, filename)
    
    # Create the PDF document in landscape mode for better table display
    doc = SimpleDocTemplate(
        filepath,
        pagesize=landscape(A4),
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=1*inch,
        bottomMargin=1*inch,
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.grey,
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.whitesmoke,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_LEFT,
        fontName='Helvetica',
        leading=12
    )
    
    # Add title
    title = Paragraph("Risk Report", title_style)
    elements.append(title)
    
    # Add current date
    current_date = datetime.now().strftime('%d/%m/%Y')
    date_text = Paragraph(f"Report Date: {current_date}", subtitle_style)
    elements.append(date_text)
    
    # Add filter information if provided
    if filters_applied:
        filter_text = "Filters Applied: " + ", ".join([f"{k}: {v}" for k, v in filters_applied.items()])
        filter_para = Paragraph(filter_text, subtitle_style)
        elements.append(filter_para)
    
    # Add summary statistics
    total_risks = risks_queryset.count()
    summary_style = ParagraphStyle(
        'Summary',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=20,
        alignment=TA_LEFT,
        fontName='Helvetica'
    )
    summary_text = f"<b>Total Risks:</b> {total_risks}"
    summary_para = Paragraph(summary_text, summary_style)
    elements.append(summary_para)
    
    elements.append(Spacer(1, 0.25*inch))
    
    # Create table data
    table_data = []
    
    # Table headers
    headers = [
        Paragraph("<b>Risk ID</b>", header_style),
        Paragraph("<b>Risk Title</b>", header_style),
        Paragraph("<b>Rating</b>", header_style),
        Paragraph("<b>Mitigation</b>", header_style),
        Paragraph("<b>Mitigation Status</b>", header_style),
        Paragraph("<b>Risk Owner</b>", header_style),
        Paragraph("<b>Due Date</b>", header_style),
    ]
    table_data.append(headers)
    
    # Add risk data
    risks_queryset = risks_queryset.order_by('-score', 'department__name', 'risk_number')
    for risk in risks_queryset:
        # Calculate risk rating based on score
        score = risk.likelihood * risk.impact if risk.likelihood and risk.impact else 0
        if score >= 20:
            rating = "Critical"
            rating_color = colors.HexColor('#c0392b')
        elif score >= 15:
            rating = "High"
            rating_color = colors.HexColor('#e74c3c')
        elif score >= 8:
            rating = "Medium"
            rating_color = colors.HexColor('#f39c12')
        else:
            rating = "Low"
            rating_color = colors.HexColor('#27ae60')
        
        # Get mitigation information - include up to 5 mitigations joined into one cell
        mitigations = list(risk.mitigations.all().order_by('due_date')[:5])
        if mitigations:
            mit_lines = []
            mit_status_lines = []
            for m in mitigations:
                action = (m.action or m.description or '').strip()
                owner = getattr(m.responsible_person, 'name', str(m.responsible_person)) if getattr(m, 'responsible_person', None) else ''
                due = m.due_date.strftime('%d/%m/%Y') if getattr(m, 'due_date', None) else 'No due'
                status_val = None
                if hasattr(m, 'get_status_display'):
                    try:
                        status_val = m.get_status_display()
                    except Exception:
                        status_val = str(getattr(m, 'status', '—'))
                else:
                    status_val = str(getattr(m, 'status', '—'))

                parts = []
                if action:
                    parts.append(wrap_text(action, max_length=80))
                if owner:
                    parts.append(f"Owner: {owner}")
                parts.append(f"Due: {due}")
                mit_lines.append(' | '.join(parts))
                mit_status_lines.append(str(status_val).replace('_', ' ').title())

            mitigation_text = '\n'.join(mit_lines)
            mitigation_status_text = '\n'.join(mit_status_lines)
            due_date = mitigations[0].due_date.strftime('%d/%m/%Y') if mitigations[0].due_date else 'N/A'
        else:
            mitigation_text = "No mitigation plan"
            mitigation_status_text = '—'
            due_date = "N/A"
        
        # Get risk owner
        risk_owner = risk.risk_owner.name if risk.risk_owner else "Unassigned"
        
        # Wrap long text and include short description under title (HTML line breaks)
        short_desc = wrap_text(risk.description or '', max_length=140)
        title_html = f"<b>{risk.title}</b>"
        if short_desc:
            # use <br/> to force line breaks within Paragraph
            title_html += f"<br/><font size=9 color=#555555>{short_desc}</font>"
        
        # Create rating paragraph with color
        rating_style = ParagraphStyle(
            'Rating',
            parent=cell_style,
            textColor=rating_color,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER
        )
        
        # Prepare Paragraphs for each cell; ensure mitigation lines use HTML <br/>
        title_para = Paragraph(title_html, cell_style)
        mitigation_html = mitigation_text.replace('\n', '<br/><br/>')
        mitigation_para = Paragraph(mitigation_html, cell_style)
        status_html = mitigation_status_text.replace('\n', '<br/><br/>')
        status_para = Paragraph(status_html, cell_style)
        row = [
            Paragraph(str(risk.risk_id), cell_style),  # Use the property
            title_para,
            Paragraph(f"{rating}<br/>({score})", rating_style),
            mitigation_para,
            status_para,
            Paragraph(risk_owner, cell_style),
            Paragraph(due_date, cell_style),
        ]
        table_data.append(row)
    
    # Create table
    # Compute available width between margins and allocate sensible column proportions
    left_margin = 0.75 * inch
    right_margin = 0.75 * inch
    page_width = landscape(A4)[0]
    avail_width = page_width - left_margin - right_margin
    # Columns: Risk ID, Title, Rating, Mitigation, Mitigation Status, Risk Owner, Due Date
    # Slightly reduce Mitigation column and increase Mitigation Status so status fits better
    col_widths = [avail_width * 0.06,  # Risk ID
                  avail_width * 0.30,  # Title + description
                  avail_width * 0.10,  # Rating
                  avail_width * 0.30,  # Mitigation (reduced)
                  avail_width * 0.10,  # Mitigation Status (increased)
                  avail_width * 0.08,  # Risk Owner (reduced)
                  avail_width * 0.06]  # Due Date
    
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    # Table styling
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Risk ID centered
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Rating centered
        ('ALIGN', (5, 1), (5, -1), 'CENTER'),  # Due Date centered
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1a237e')),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
    ]))
    
    elements.append(table)
    
    # Add footer note
    elements.append(Spacer(1, 0.3*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique'
    )
    footer_text = "This report is confidential and intended for authorized personnel only."
    footer_para = Paragraph(footer_text, footer_style)
    elements.append(footer_para)
    
    # Build PDF with custom canvas for page numbers
    doc.build(elements, canvasmaker=NumberedCanvas)
    
    return filepath, filename


def generate_detailed_risk_report_pdf(risks_queryset, include_assessments=True, include_indicators=True):
    """
    Generate a more detailed PDF report with risk assessments and indicators.
    
    Args:
        risks_queryset: Django queryset of Risk objects
        include_assessments: Boolean to include assessment history
        include_indicators: Boolean to include KPI indicators
    
    Returns:
        tuple: (file_path, filename) of the generated PDF
    """
    # Create media directory
    media_root = settings.MEDIA_ROOT
    reports_dir = os.path.join(media_root, 'risk_reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'detailed_risk_report_{timestamp}.pdf'
    filepath = os.path.join(reports_dir, filename)
    
    # Create PDF
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=1*inch,
        bottomMargin=1*inch,
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    elements.append(Paragraph("Detailed Risk Report", title_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Process each risk
    for idx, risk in enumerate(risks_queryset):
        if idx > 0:
            elements.append(PageBreak())
        
        # Risk header
        risk_header_style = ParagraphStyle(
            'RiskHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=10,
            fontName='Helvetica-Bold'
        )
        elements.append(Paragraph(f"Risk ID: {risk.risk_id} - {risk.title}", risk_header_style))
        elements.append(Spacer(1, 0.1*inch))
        
        # Risk details table
        score = risk.likelihood * risk.impact if risk.likelihood and risk.impact else 0
        
        details_data = [
            ['Department:', risk.department.name if risk.department else 'N/A'],
            ['Category:', risk.category.name if risk.category else 'N/A'],
            ['Risk Owner:', risk.risk_owner.name if risk.risk_owner else 'Unassigned'],
            ['Likelihood:', str(risk.likelihood) if risk.likelihood else 'N/A'],
            ['Impact:', str(risk.impact) if risk.impact else 'N/A'],
            ['Risk Score:', f"{score} ({'Critical' if score >= 20 else 'High' if score >= 15 else 'Medium' if score >= 8 else 'Low'})"],
            ['Status:', risk.status.title() if risk.status else 'N/A'],
        ]
        
        details_table = Table(details_data, colWidths=[1.5*inch, 4*inch])
        details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eaf6')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(details_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Description
        elements.append(Paragraph("<b>Description:</b>", styles['Heading3']))
        elements.append(Paragraph(risk.description or "No description provided.", styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Mitigations
        mitigations = risk.mitigations.all()
        elements.append(Paragraph("<b>Mitigation Plans:</b>", styles['Heading3']))
        
        if mitigations.exists():
            mit_data: list = [['Action', 'Status', 'Responsible', 'Due Date']]
            for mit in mitigations:
                # Ensure responsible_person is converted to a display string (may be FK object)
                responsible_display = (
                    getattr(mit.responsible_person, 'name', str(mit.responsible_person))
                    if getattr(mit, 'responsible_person', None) else 'N/A'
                )
                mit_data.append([
                    Paragraph(wrap_text(mit.action, 40), styles['Normal']),
                    Paragraph(mit.get_status_display() if hasattr(mit, 'get_status_display') else 'N/A', styles['Normal']),
                    Paragraph(responsible_display, styles['Normal']),
                    Paragraph(mit.due_date.strftime('%d/%m/%Y') if mit.due_date else 'N/A', styles['Normal'])
                ])
            
            mit_table = Table(mit_data, colWidths=[2.5*inch, 1*inch, 1.2*inch, 1*inch])
            mit_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ]))
            elements.append(mit_table)
        else:
            elements.append(Paragraph("No mitigation plans defined.", styles['Normal']))
        
        elements.append(Spacer(1, 0.1*inch))

        # --- Recent Changes section: include latest risk assessment, indicator assessments and activity logs ---
        elements.append(Paragraph("<b>Recent Changes:</b>", styles['Heading3']))

        # Latest Risk Assessment (if any)
        try:
            latest_assessment = risk.assessments.filter(is_current=True).order_by('-assessment_date').first() or risk.assessments.order_by('-assessment_date').first()
        except Exception:
            latest_assessment = None

        if latest_assessment:
            asst_lines = []
            asst_lines.append(f"Assessment Date: {latest_assessment.assessment_date.strftime('%d/%m/%Y') if latest_assessment.assessment_date else 'N/A'}")
            assessor = getattr(latest_assessment.assessor, 'get_full_name', None)
            if callable(assessor):
                asst_lines.append(f"Assessor: {latest_assessment.assessor.get_full_name()}")
            else:
                asst_lines.append(f"Assessor: {getattr(latest_assessment.assessor, 'username', 'N/A') if latest_assessment.assessor else 'N/A'}")
            if latest_assessment.overall_result:
                asst_lines.append(f"Result: {wrap_text(latest_assessment.overall_result, 120)}")
            if latest_assessment.changes_since_last:
                asst_lines.append(f"Changes: {wrap_text(latest_assessment.changes_since_last, 120)}")
            if latest_assessment.recommendations:
                asst_lines.append(f"Recommendations: {wrap_text(latest_assessment.recommendations, 120)}")

            elements.append(Paragraph('<br/>'.join(asst_lines), styles['Normal']))
        else:
            elements.append(Paragraph("No recent risk assessment found.", styles['Normal']))

        elements.append(Spacer(1, 0.1*inch))

        # Latest Indicator Assessments (one per indicator)
        try:
            indicators = risk.indicators.all()
        except Exception:
            indicators = []

        if indicators:
            ind_lines = []
            for ind in indicators:
                try:
                    latest_ind_ass = ind.assessments.order_by('-assessment_date').first()
                except Exception:
                    latest_ind_ass = None

                if latest_ind_ass:
                    by = latest_ind_ass.assessed_by.get_full_name() if latest_ind_ass.assessed_by and hasattr(latest_ind_ass.assessed_by, 'get_full_name') else (getattr(latest_ind_ass.assessed_by, 'username', 'N/A') if latest_ind_ass.assessed_by else 'N/A')
                    ind_lines.append(f"{ind.name if getattr(ind, 'name', None) else ind.pk}: {latest_ind_ass.status} on {latest_ind_ass.assessment_date.strftime('%d/%m/%Y') if latest_ind_ass.assessment_date else 'N/A'} by {by}")

            if ind_lines:
                # Limit to first 10 lines to avoid overly long report
                elements.append(Paragraph('<br/>'.join(ind_lines[:10]), styles['Normal']))
            else:
                elements.append(Paragraph("No indicator assessments available.", styles['Normal']))
        else:
            elements.append(Paragraph("No indicators defined for this risk.", styles['Normal']))

        elements.append(Spacer(1, 0.1*inch))

        # Recent activity logs for this risk (object_id or context.risk_id)
        try:
            recent_logs = ActivityLog.objects.select_related('user').filter(
                Q(object_type__iexact='Risk', object_id=str(risk.pk)) |
                Q(context__risk_id=risk.pk) |
                Q(object_type__iexact='Mitigation', context__risk_id=risk.pk)
            ).order_by('-created_at')[:8]
        except Exception:
            recent_logs = []

        if recent_logs:
            log_lines = []
            for lg in recent_logs:
                user_display = lg.user.get_full_name() if lg.user and hasattr(lg.user, 'get_full_name') else (getattr(lg.user, 'username', 'System') if lg.user else 'System')
                ts = lg.created_at.strftime('%d/%m/%Y %H:%M') if getattr(lg, 'created_at', None) else ''
                # Shorten description
                descr = (lg.description or '')
                log_lines.append(f"[{ts}] {user_display}: {wrap_text(descr, 140)}")

            elements.append(Paragraph('<br/>'.join(log_lines), styles['Normal']))
        else:
            elements.append(Paragraph("No recent activity recorded for this risk.", styles['Normal']))

        elements.append(Spacer(1, 0.15*inch))
    
    # Build PDF
    doc.build(elements, canvasmaker=NumberedCanvas)
    
    return filepath, filename