"""PDF report generation using ReportLab."""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Frame,
    PageTemplate
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas

import config

logger = logging.getLogger(__name__)


def _add_gradient_background(canvas_obj, doc):
    """
    Add a visible gradient background to the page.
    Blue gradient that fades from top to middle of page.
    
    Args:
        canvas_obj: ReportLab canvas object
        doc: Document object
    """
    canvas_obj.saveState()
    
    # Create a smooth gradient from blue to white
    # Fades from top to middle of page
    width, height = letter
    
    # Use a visible blue for better aesthetics
    gradient_color = colors.HexColor('#B8D5E8')  # Original blue
    
    # Create smooth gradient with many steps for seamless blend
    # Goes from top to middle of page (50% of height)
    num_steps = 50  # More steps = smoother gradient
    gradient_height = height * 0.5  # Gradient covers top half of page
    step_height = gradient_height / num_steps
    
    for i in range(num_steps):
        # Calculate alpha that goes from full color to completely transparent
        alpha = 1 - (i / num_steps)
        
        # Create color with decreasing opacity
        color = colors.Color(
            gradient_color.red,
            gradient_color.green,
            gradient_color.blue,
            alpha=alpha * 0.9  # Increased from 0.7 to 0.9 for more visibility
        )
        
        canvas_obj.setFillColor(color)
        y_pos = height - (i * step_height)
        canvas_obj.rect(0, y_pos - step_height, width, step_height, fill=1, stroke=0)
    
    canvas_obj.restoreState()


def _add_header(canvas_obj, doc):
    """
    Add header with Gavin AI logo text to each page.
    
    Args:
        canvas_obj: ReportLab canvas object
        doc: Document object
    """
    canvas_obj.saveState()
    width, height = letter
    
    # Add "GAVIN AI" text logo in top right
    canvas_obj.setFont('Times-Bold', 11)
    canvas_obj.setFillColor(colors.HexColor('#4A90E2'))
    canvas_obj.drawRightString(width - 50, height - 40, "GAVIN AI")
    
    canvas_obj.restoreState()


def _create_first_page_template(canvas_obj, doc):
    """
    Create custom page template for first page with gradient and header.
    
    Args:
        canvas_obj: ReportLab canvas object
        doc: Document object
    """
    _add_gradient_background(canvas_obj, doc)
    _add_header(canvas_obj, doc)


def _create_later_page_template(canvas_obj, doc):
    """
    Create custom page template for later pages with gradient and header.
    Uses smaller top margin for natural content flow.
    
    Args:
        canvas_obj: ReportLab canvas object
        doc: Document object
    """
    _add_gradient_background(canvas_obj, doc)
    _add_header(canvas_obj, doc)


def _format_time(minutes: float) -> str:
    """
    Format time in a human-readable way.
    
    Args:
        minutes: Time in minutes (can be fractional)
        
    Returns:
        Formatted string like "1m 30s" or "45s" or "2h 15m"
        Values less than 1 minute show in seconds only
        Omits .0 decimals (e.g., "45.0%" becomes "45%")
    """
    total_seconds = int(minutes * 60)
    
    # Less than 1 minute - show seconds only
    if total_seconds < 60:
        return f"{total_seconds}s"
    
    hours = total_seconds // 3600
    remaining_seconds = total_seconds % 3600
    mins = remaining_seconds // 60
    secs = remaining_seconds % 60
    
    if hours > 0:
        if secs > 0:
            return f"{hours}h {mins}m {secs}s"
        else:
            return f"{hours}h {mins}m"
    else:
        if secs > 0:
            return f"{mins}m {secs}s"
        else:
            return f"{mins}m"


def generate_report(
    stats: Dict[str, Any],
    session_id: str,
    start_time: datetime,
    end_time: Optional[datetime] = None,
    output_dir: Optional[Path] = None
) -> Path:
    """
    Generate a combined PDF report with summary statistics and all session logs.
    
    Page 1: Title, metadata, Summary Statistics table
    Page 2+: Full session logs (all events, no truncation)
    
    Args:
        stats: Statistics dictionary from analytics.compute_statistics()
        session_id: Unique session identifier
        start_time: Session start time
        end_time: Session end time (optional)
        output_dir: Output directory (defaults to config.REPORTS_DIR)
        
    Returns:
        Path to the generated PDF file
    """
    if output_dir is None:
        output_dir = config.REPORTS_DIR
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    filename = f"{session_id}.pdf"
    filepath = output_dir / filename
    
    # Create PDF document with custom template
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=letter,
        rightMargin=60,
        leftMargin=60,
        topMargin=60,
        bottomMargin=60
    )
    
    # Build the story (content)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles with Georgia-like font (Times-Roman)
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName='Times-Bold',
        fontSize=28,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=20,
        spaceBefore=20,
        alignment=TA_LEFT,
        leading=34
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontName='Times-Italic',
        fontSize=12,
        textColor=colors.HexColor('#7F8C8D'),
        spaceAfter=30,
        alignment=TA_LEFT
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName='Times-Bold',
        fontSize=18,
        textColor=colors.HexColor('#34495E'),
        spaceAfter=20,
        spaceBefore=20,
        alignment=TA_LEFT,
        leading=24
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=12,
        textColor=colors.HexColor('#2C3E50'),
        leading=17,
        spaceAfter=8
    )
    
    # ===== PAGE 1: Title + Summary Statistics =====
    
    # Title
    story.append(Paragraph("Focus Session Report", title_style))
    
    # Session metadata as subtitle with date and time range
    date_str = start_time.strftime("%B %d, %Y")
    start_time_str = start_time.strftime("%I:%M%p").lstrip('0').replace(' ', '')
    
    if end_time:
        end_time_str = end_time.strftime("%I:%M%p").lstrip('0').replace(' ', '')
        metadata = f"{date_str} from {start_time_str} - {end_time_str}"
    else:
        metadata = f"{date_str} from {start_time_str} - {start_time_str}"
    
    story.append(Paragraph(metadata, subtitle_style))
    
    # Statistics section
    story.append(Paragraph("Summary Statistics", heading_style))
    
    # Calculate focus percentage (present time / total time)
    focus_pct = (stats['present_minutes'] / stats['total_minutes'] * 100) if stats['total_minutes'] > 0 else 0
    focus_pct_str = f"{int(focus_pct)}%" if focus_pct == int(focus_pct) else f"{focus_pct:.1f}%"
    
    # Build table data, only including rows with non-zero values
    stats_data = [['Category', 'Duration']]
    
    # Track which rows we add for color coding later
    row_types = []
    
    # Add rows conditionally based on non-zero values
    if stats['present_minutes'] > 0:
        stats_data.append(['Present at Desk', _format_time(stats['present_minutes'])])
        row_types.append('present')
    
    if stats['away_minutes'] > 0:
        stats_data.append(['Away from Desk', _format_time(stats['away_minutes'])])
        row_types.append('away')
    
    if stats['phone_minutes'] > 0:
        stats_data.append(['Phone Usage', _format_time(stats['phone_minutes'])])
        row_types.append('phone')
    
    # Always add Total Time and Focus Rate
    stats_data.append(['Total Time', _format_time(stats['total_minutes'])])
    row_types.append('total')
    stats_data.append(['Focus Rate', focus_pct_str])
    row_types.append('focus')
    
    stats_table = Table(stats_data, colWidths=[3.0 * inch, 3.0 * inch])
    
    # Build table style dynamically based on which rows are present
    table_style = [
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A90E2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 13),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        # Data rows (regular)
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFB')),
        ('FONTNAME', (0, 1), (0, -1), 'Times-Roman'),
        ('FONTNAME', (1, 1), (1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#4A90E2')),
        ('LINEBELOW', (0, 1), (-1, -2), 0.5, colors.HexColor('#E0E6ED')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2C3E50')),
    ]
    
    # Apply colors dynamically based on which rows exist
    for i, row_type in enumerate(row_types, 1):  # Start at 1 to skip header
        if row_type == 'present':
            table_style.append(('TEXTCOLOR', (0, i), (0, i), colors.HexColor('#1B7A3D')))
        elif row_type in ['away', 'phone']:
            table_style.append(('TEXTCOLOR', (0, i), (0, i), colors.HexColor('#C62828')))
        elif row_type in ['total', 'focus']:
            # Make Total Time and Focus Rate bold in both columns
            table_style.append(('FONTNAME', (0, i), (0, i), 'Times-Bold'))
            table_style.append(('FONTNAME', (1, i), (1, i), 'Times-Bold'))
    
    stats_table.setStyle(TableStyle(table_style))
    
    story.append(stats_table)
    
    # ===== PAGE 2+: Session Logs =====
    
    # Force logs to start on second page
    story.append(PageBreak())
    story.append(Spacer(1, 0.1 * inch))
    
    # Logs heading
    story.append(Paragraph("Session Logs", heading_style))
    
    # Get all events
    events = stats.get('events', [])
    
    if events:
        # Filter out events with 0 duration
        non_zero_events = [e for e in events if e.get('duration_minutes', 0) > 0]
        
        if non_zero_events:
            # Build table with ALL events (no limit)
            timeline_data = [['Time', 'Activity', 'Duration']]
            for event in non_zero_events:
                timeline_data.append([
                    f"{event['start']} - {event['end']}",
                    event['type_label'],
                    _format_time(event['duration_minutes'])
                ])
            
            timeline_table = Table(timeline_data, colWidths=[2.4 * inch, 2.2 * inch, 1.4 * inch])
            
            # Build table style
            logs_table_style = [
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A90E2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                # Data rows
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFB')),
                ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#4A90E2')),
                ('LINEBELOW', (0, 1), (-1, -2), 0.5, colors.HexColor('#E0E6ED')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2C3E50')),
            ]
            
            # Add color coding for Activity column based on event type
            for i, event in enumerate(non_zero_events, 1):
                event_type = event.get('type', '')
                if event_type == 'present':
                    logs_table_style.append(('TEXTCOLOR', (1, i), (1, i), colors.HexColor('#1B7A3D')))
                elif event_type in ['away', 'phone_suspected']:
                    logs_table_style.append(('TEXTCOLOR', (1, i), (1, i), colors.HexColor('#C62828')))
            
            timeline_table.setStyle(TableStyle(logs_table_style))
            story.append(timeline_table)
        else:
            story.append(Paragraph("No events recorded.", body_style))
    else:
        story.append(Paragraph("No events recorded.", body_style))
    
    story.append(Spacer(1, 0.5 * inch))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontName='Times-Italic',
        fontSize=9,
        textColor=colors.HexColor('#95A5A6'),
        alignment=TA_CENTER
    )
    
    footer_text = "Generated by Gavin AI"
    story.append(Paragraph(footer_text, footer_style))
    
    # Build PDF with custom page template
    try:
        doc.build(story, onFirstPage=_create_first_page_template, onLaterPages=_create_later_page_template)
        logger.info(f"PDF report generated: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise
