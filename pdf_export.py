from __future__ import annotations

import os
import xml.sax.saxutils as saxutils
from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


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


# ── Chart Builders ───────────────────────────────────────────────────

_SENTIMENT_COLORS = {
    "Positive": colors.HexColor("#2ecc71"),
    "Negative": colors.HexColor("#e74c3c"),
    "Neutral":  colors.HexColor("#95a5a6"),
    "Mixed":    colors.HexColor("#f39c12"),
}


def _sentiment_pie(sentiment_pct: dict[str, float]) -> Drawing:
    d = Drawing(170 * mm, 75 * mm)
    pc = Pie()
    pc.x = 30 * mm
    pc.y = 10 * mm
    pc.width = 50 * mm
    pc.height = 50 * mm

    labels_order = ["Positive", "Negative", "Neutral", "Mixed"]
    final_data, final_labels, final_colors = [], [], []
    for lbl in labels_order:
        val = sentiment_pct.get(lbl, 0)
        if val > 0:
            final_data.append(val)
            final_labels.append(f"{lbl} ({val}%)")
            final_colors.append(_SENTIMENT_COLORS.get(lbl, colors.HexColor("#bdc3c7")))

    if not final_data:
        final_data, final_labels, final_colors = [100], ["No data"], [colors.HexColor("#bdc3c7")]

    pc.data = final_data
    pc.labels = None  # Use legend instead to avoid overlap
    pc.slices.strokeWidth = 0.5
    pc.slices.fontName = "Helvetica"
    pc.slices.fontSize = 8
    for i, c in enumerate(final_colors):
        pc.slices[i].fillColor = c
        pc.slices[i].popout = 2

    # Legend to the right
    legend = Legend()
    legend.x = 100 * mm
    legend.y = 45 * mm
    legend.dx = 8
    legend.dy = 8
    legend.deltay = 14
    legend.fontName = "Helvetica"
    legend.fontSize = 9
    legend.alignment = "right"
    legend.columnMaximum = 5
    legend.colorNamePairs = list(zip(final_colors, final_labels))

    d.add(pc)
    d.add(legend)
    return d


def _bar_chart_with_labels(
    dist: dict[Any, int],
    x_labels: list,
    bar_color: str = "#3498db",
    total_for_pct: int | None = None,
) -> Drawing:
    """Bar chart with value labels above each bar and optional percentage annotations."""
    d = Drawing(170 * mm, 75 * mm)
    bc = VerticalBarChart()
    bc.x = 20 * mm
    bc.y = 15 * mm
    bc.height = 42 * mm
    bc.width = 135 * mm

    values = [dist.get(k, 0) for k in x_labels]
    bc.data = [values]

    display_labels = [str(k) for k in x_labels]
    # Truncate long category names to prevent overlap
    bc.categoryAxis.categoryNames = [
        (lbl[:10] + "…" if len(lbl) > 12 else lbl) for lbl in display_labels
    ]
    bc.categoryAxis.labels.fontName = "Helvetica"
    bc.categoryAxis.labels.fontSize = 7

    max_val = max(values) if values else 1
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = max_val + max(1, int(max_val * 0.15))
    bc.valueAxis.valueStep = max(1, max_val // 5) if max_val > 0 else 1
    bc.valueAxis.labels.fontName = "Helvetica"
    bc.valueAxis.labels.fontSize = 7

    bc.bars[0].fillColor = colors.HexColor(bar_color)
    bc.strokeColor = colors.HexColor("#9fc1d8")

    d.add(bc)

    # Value labels above each bar
    bar_width = bc.width / max(len(values), 1)
    for i, val in enumerate(values):
        if val == 0:
            continue
        x_pos = bc.x + (i + 0.5) * bar_width
        y_pos = bc.y + bc.height * (val / bc.valueAxis.valueMax) + 2 * mm

        label_text = str(val)
        if total_for_pct and total_for_pct > 0:
            pct = round((val / total_for_pct) * 100, 1)
            label_text = f"{val} ({pct}%)"

        s = String(x_pos, y_pos, label_text,
                    fontName="Helvetica", fontSize=7,
                    fillColor=colors.HexColor("#0f3d5e"),
                    textAnchor="middle")
        d.add(s)

    return d


# ── Executive Summary Generator ──────────────────────────────────────

def _generate_executive_summary(analysis: dict[str, Any]) -> str:
    """Generates a data-driven executive summary paragraph from actual metrics."""
    stats = analysis.get("stats", {})
    sentiment_pct = analysis.get("sentiment_percent", {})
    avg_rating = analysis.get("average_rating")
    total = stats.get("total", 0)
    confidence = analysis.get("overall_confidence", 0)

    pos = sentiment_pct.get("Positive", 0)
    neg = sentiment_pct.get("Negative", 0)
    mixed = sentiment_pct.get("Mixed", 0)

    parts = [f"This report analyzes <b>{total}</b> customer feedback entries"]
    if avg_rating is not None:
        parts[0] += f" with an average rating of <b>{avg_rating}/5</b>"
    parts[0] += f" (analysis confidence: <b>{confidence}%</b>)."

    # Sentiment summary
    if pos >= 60:
        parts.append(f"Overall sentiment is strongly positive at <b>{pos}%</b>, indicating high customer satisfaction.")
    elif pos >= 40:
        parts.append(f"Sentiment leans positive (<b>{pos}%</b>) but with notable negative feedback at <b>{neg}%</b>.")
    elif neg >= 40:
        parts.append(f"Sentiment is predominantly negative (<b>{neg}%</b>), signaling critical issues requiring attention.")
    else:
        parts.append(f"Sentiment is distributed across positive (<b>{pos}%</b>), negative (<b>{neg}%</b>), and mixed (<b>{mixed}%</b>) signals.")

    # Category insight
    categories = analysis.get("categories", {})
    if categories:
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        top_cat, top_count = sorted_cats[0]
        if top_count > 0:
            total_cat = sum(categories.values())
            cat_pct = round((top_count / total_cat) * 100, 1) if total_cat > 0 else 0
            parts.append(f"<b>{top_cat}</b> is the most discussed category at <b>{cat_pct}%</b> of categorized mentions.")

    return " ".join(parts)


# ── Main PDF Builder ─────────────────────────────────────────────────

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
    summary_prose_style = ParagraphStyle(
        "SummaryProse",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2c3e50"),
        spaceBefore=4,
        spaceAfter=8,
        borderPadding=6,
        backColor=colors.HexColor("#f0f8ff"),
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
    total = stats.get("total", 0)

    # ── Page 1: Overview + Charts ────────────────────────────────────

    elements = [
        Paragraph("Customer Feedback Executive Summary", title_style),
        Paragraph(f"File: {_safe_text(file_meta.get('name'))}", body_style),
        Paragraph(f"Report Generated: {generated_at}", body_style),
        Spacer(1, 6),
        Paragraph(_generate_executive_summary(analysis), summary_prose_style),
        Spacer(1, 6),
    ]

    # Snapshot table with confidence
    mixed_pct = sentiment.get("Mixed", 0)
    summary_rows = [
        ["Metric", "Value"],
        ["Total Feedback", _safe_text(stats.get("total"))],
        ["Average Length", _safe_text(stats.get("avg_length"))],
        ["Average Rating", _safe_text(analysis.get("average_rating"))],
        ["Analysis Confidence", f"{_safe_text(analysis.get('overall_confidence', 0), '0')}%"],
        ["Positive Sentiment", f"{_safe_text(sentiment.get('Positive', 0), '0')}%"],
        ["Negative Sentiment", f"{_safe_text(sentiment.get('Negative', 0), '0')}%"],
        ["Mixed Sentiment", f"{_safe_text(mixed_pct, '0')}%"],
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
                ("FONTSIZE", (0, 0), (-1, -1), 9),
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

    elements.extend([
        Paragraph("Snapshot", section_style),
        summary_table,
        Spacer(1, 8),
        Paragraph("Sentiment Distribution", section_style),
        _sentiment_pie(sentiment),
        Spacer(1, 4),
    ])

    if analysis.get("rating_distribution"):
        elements.append(Paragraph("Rating Distribution", section_style))
        elements.append(
            _bar_chart_with_labels(
                analysis["rating_distribution"], [1, 2, 3, 4, 5],
                bar_color="#8e44ad", total_for_pct=total
            )
        )
        elements.append(Spacer(1, 4))

    categories = analysis.get("categories", {})
    if categories:
        elements.append(Paragraph("Category Distribution", section_style))
        elements.append(
            _bar_chart_with_labels(
                categories, list(categories.keys()),
                bar_color="#3498db", total_for_pct=total
            )
        )
        elements.append(Spacer(1, 4))

    elements.append(PageBreak())

    # ── Page 2: Business Insights + Priorities ───────────────────────

    elements.extend([
        Paragraph("Business Insights", title_style),
    ])

    # Strengths
    elements.append(Paragraph("Key Strengths", section_style))
    strengths = analysis.get("business_insights", {}).get("top_strengths", [])
    if strengths:
        for s in strengths:
            elements.append(Paragraph(f"\u2022 {_safe_text(s)}", body_style))
    else:
        elements.append(Paragraph("Stable performance maintained.", body_style))

    # Complaints
    elements.append(Paragraph("Core Complaints", section_style))
    complaints = analysis.get("business_insights", {}).get("top_complaints", [])
    if complaints:
        for c in complaints:
            elements.append(Paragraph(f"\u2022 {_safe_text(c)}", body_style))
    else:
        elements.append(Paragraph("No significant frictional clusters detected.", body_style))

    elements.append(Spacer(1, 8))

    # Priorities with percentages
    elements.append(Paragraph("Top 3 Priorities", section_style))
    if priorities:
        for idx, priority in enumerate(priorities[:3], start=1):
            title = _safe_text(priority.get("title"))
            evidence = _safe_text(priority.get("evidence"))
            action = _safe_text(priority.get("action"))
            score = priority.get("score", 0)
            elements.append(
                Paragraph(f"{idx}. <b>{title}</b> &nbsp; <font size='8' color='#7f8c8d'>(score: {score})</font>", body_style)
            )
            elements.append(Paragraph(f"Evidence: {evidence}", body_style))
            elements.append(Paragraph(f"Action: {action}", body_style))
            elements.append(Spacer(1, 4))
    else:
        elements.append(Paragraph("No priority insights available.", body_style))

    # Category breakdown with counts and percentages
    if categories and total > 0:
        elements.append(Paragraph("Category Breakdown", section_style))
        cat_rows = [["Category", "Mentions", "% of Total"]]
        for cat_name, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            pct = round((count / total) * 100, 1)
            cat_rows.append([cat_name, str(count), f"{pct}%"])
        cat_table = Table(cat_rows, colWidths=[55 * mm, 40 * mm, 55 * mm])
        cat_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f2f8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f3d5e")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9fc1d8")),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fbfe")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(cat_table)
        elements.append(Spacer(1, 8))

    # Recommended Actions
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
