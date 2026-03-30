from __future__ import annotations

import os
import xml.sax.saxutils as saxutils
from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

def _safe_text(value: Any, default: str = "N/A") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return saxutils.escape(text) if text else default


def _draw_header_footer(canv, doc, brand_name: str, generated_at: str):
    canv.saveState()
    width, height = A4

    # Header accent and brand
    canv.setFillColor(colors.HexColor("#0f3d5e"))
    canv.rect(doc.leftMargin, height - 16 * mm, width - doc.leftMargin - doc.rightMargin, 2.2, fill=1, stroke=0)
    canv.setFont("Helvetica-Bold", 10)
    canv.setFillColor(colors.HexColor("#0f3d5e"))
    canv.drawString(doc.leftMargin, height - 12.5 * mm, brand_name)

    canv.setFont("Helvetica", 8)
    canv.setFillColor(colors.HexColor("#4f6f85"))
    canv.drawRightString(width - doc.rightMargin, height - 12.5 * mm, f"Generated: {generated_at}")

    # Footer line + page number
    canv.setStrokeColor(colors.HexColor("#9fc1d8"))
    canv.setLineWidth(0.7)
    canv.line(doc.leftMargin, 12 * mm, width - doc.rightMargin, 12 * mm)
    canv.setFont("Helvetica", 8)
    canv.setFillColor(colors.HexColor("#4f6f85"))
    canv.drawString(doc.leftMargin, 8.2 * mm, "Confidential - Internal Use")
    canv.drawRightString(width - doc.rightMargin, 8.2 * mm, f"Page {canv.getPageNumber()}")
    canv.restoreState()


def build_executive_summary_pdf(analysis: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    brand_name = os.getenv("REPORT_BRAND_NAME", "Customer Feedback Pulse")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=24 * mm,
        bottomMargin=18 * mm,
        title="Customer Feedback Executive Summary",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f3d5e"),
        spaceAfter=8,
    )
    section_style = ParagraphStyle(
        "SectionStyle",
        parent=styles["Heading2"],
        fontSize=12,
        leading=14,
        textColor=colors.HexColor("#1b4f72"),
        spaceBefore=8,
        spaceAfter=5,
    )
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["BodyText"],
        fontSize=10,
        leading=13,
    )

    file_meta = analysis.get("file", {}) if isinstance(analysis.get("file"), dict) else {}
    stats = analysis.get("stats", {}) if isinstance(analysis.get("stats"), dict) else {}
    sentiment = (
        analysis.get("sentiment_percent", {})
        if isinstance(analysis.get("sentiment_percent"), dict)
        else {}
    )
    suggestions = analysis.get("suggestions", []) if isinstance(analysis.get("suggestions"), list) else []
    priorities = (
        analysis.get("priority_insights", [])
        if isinstance(analysis.get("priority_insights"), list)
        else []
    )

    elements = [
        Paragraph("Customer Feedback Executive Summary", title_style),
        Paragraph(f"File: {_safe_text(file_meta.get('name'))}", body_style),
        Paragraph(f"Report Generated: {generated_at}", body_style),
        Spacer(1, 8),
    ]

    summary_rows = [
        ["Metric", "Value"],
        ["Total Feedback", _safe_text(stats.get("total"))],
        ["Average Length", _safe_text(stats.get("avg_length"))],
        ["Average Rating", _safe_text(analysis.get("average_rating"))],
        ["Positive Sentiment", f"{_safe_text(sentiment.get('Positive', 0), '0')}%"],
        ["Negative Sentiment", f"{_safe_text(sentiment.get('Negative', 0), '0')}%"],
        ["Neutral Sentiment", f"{_safe_text(sentiment.get('Neutral', 0), '0')}%"],
    ]
    summary_table = Table(summary_rows, colWidths=[60 * mm, 95 * mm])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f2f8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f3d5e")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9fc1d8")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fbfe")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    elements.extend(
        [
            Paragraph("Snapshot", section_style),
            summary_table,
            Spacer(1, 8),
            Paragraph("Top 3 Priorities", section_style),
        ]
    )

    if priorities:
        for idx, priority in enumerate(priorities[:3], start=1):
            title = _safe_text(priority.get("title"))
            evidence = _safe_text(priority.get("evidence"))
            action = _safe_text(priority.get("action"))
            elements.append(Paragraph(f"{idx}. <b>{title}</b>", body_style))
            elements.append(Paragraph(f"Evidence: {evidence}", body_style))
            elements.append(Paragraph(f"Action: {action}", body_style))
            elements.append(Spacer(1, 4))
    else:
        elements.append(Paragraph("No priority insights available.", body_style))

    elements.append(Paragraph("Recommended Actions", section_style))
    if suggestions:
        for idx, item in enumerate(suggestions[:5], start=1):
            elements.append(Paragraph(f"{idx}. {_safe_text(item)}", body_style))
    else:
        elements.append(Paragraph("No suggested actions available.", body_style))

    doc.build(
        elements,
        onFirstPage=lambda canv, doc_ref: _draw_header_footer(canv, doc_ref, brand_name, generated_at),
        onLaterPages=lambda canv, doc_ref: _draw_header_footer(canv, doc_ref, brand_name, generated_at),
    )
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
