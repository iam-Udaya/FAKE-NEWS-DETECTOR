"""
utils.py - Shared Utilities
============================
Helper functions for export (PDF, TXT, JSON), Plotly charts,
verdict badge rendering, and Streamlit session state management.
"""

from __future__ import annotations

import io
import json
import logging
from datetime import datetime
from typing import Any

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Verdict Styling
# ─────────────────────────────────────────────────────────────────────────────

VERDICT_CONFIG = {
    "Likely Real": {
        "color": "#00c896",
        "bg": "rgba(0,200,150,0.15)",
        "icon": "✅",
        "badge_class": "badge-real",
    },
    "Suspicious": {
        "color": "#f5a623",
        "bg": "rgba(245,166,35,0.15)",
        "icon": "⚠️",
        "badge_class": "badge-suspicious",
    },
    "Likely Fake": {
        "color": "#ff4757",
        "bg": "rgba(255,71,87,0.15)",
        "icon": "❌",
        "badge_class": "badge-fake",
    },
    "Error": {
        "color": "#888",
        "bg": "rgba(136,136,136,0.1)",
        "icon": "❓",
        "badge_class": "badge-error",
    },
}


def get_verdict_config(verdict: str) -> dict:
    """Return styling config for a verdict string."""
    return VERDICT_CONFIG.get(verdict, VERDICT_CONFIG["Error"])


def score_color(score: int) -> str:
    """Map a 0-100 credibility score to a hex color."""
    if score >= 70:
        return "#00c896"
    if score >= 40:
        return "#f5a623"
    return "#ff4757"


# ─────────────────────────────────────────────────────────────────────────────
# Plotly Charts
# ─────────────────────────────────────────────────────────────────────────────

CHART_TEMPLATE = "plotly_dark"
CHART_PAPER_BG = "rgba(0,0,0,0)"
CHART_PLOT_BG = "rgba(255,255,255,0.03)"


def make_gauge_chart(score: int, title: str = "Credibility Score") -> go.Figure:
    """
    Build a Plotly gauge/indicator for the credibility score.

    Args:
        score: Integer 0-100.
        title: Chart title text.

    Returns:
        Plotly Figure object.
    """
    color = score_color(score)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            title={"text": title, "font": {"size": 18, "color": "#e0e0e0"}},
            number={"suffix": "/100", "font": {"size": 36, "color": color}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#555"},
                "bar": {"color": color, "thickness": 0.25},
                "bgcolor": "rgba(255,255,255,0.05)",
                "bordercolor": "#333",
                "steps": [
                    {"range": [0, 40], "color": "rgba(255,71,87,0.2)"},
                    {"range": [40, 70], "color": "rgba(245,166,35,0.2)"},
                    {"range": [70, 100], "color": "rgba(0,200,150,0.2)"},
                ],
                "threshold": {
                    "line": {"color": color, "width": 4},
                    "thickness": 0.75,
                    "value": score,
                },
            },
        )
    )
    fig.update_layout(
        paper_bgcolor=CHART_PAPER_BG,
        plot_bgcolor=CHART_PLOT_BG,
        font_color="#e0e0e0",
        height=280,
        margin=dict(l=30, r=30, t=40, b=10),
    )
    return fig


def make_verdict_pie(verdict_distribution: dict[str, int]) -> go.Figure:
    """
    Donut chart showing the distribution of verdicts.

    Args:
        verdict_distribution: {'Likely Real': n, 'Suspicious': n, 'Likely Fake': n}

    Returns:
        Plotly Figure object.
    """
    colors = {
        "Likely Real": "#00c896",
        "Suspicious": "#f5a623",
        "Likely Fake": "#ff4757",
    }
    labels = list(verdict_distribution.keys())
    values = list(verdict_distribution.values())
    chart_colors = [colors.get(l, "#888") for l in labels]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker=dict(colors=chart_colors, line=dict(color="#1a1a2e", width=2)),
            textinfo="label+percent",
            textfont=dict(color="#e0e0e0", size=13),
        )
    )
    fig.update_layout(
        paper_bgcolor=CHART_PAPER_BG,
        plot_bgcolor=CHART_PLOT_BG,
        font_color="#e0e0e0",
        showlegend=False,
        height=320,
        margin=dict(l=10, r=10, t=30, b=10),
        annotations=[
            dict(
                text="Verdicts",
                x=0.5,
                y=0.5,
                font_size=14,
                font_color="#aaa",
                showarrow=False,
            )
        ],
    )
    return fig


def make_trend_chart(recent_analyses: list[dict]) -> go.Figure:
    """
    Line chart of credibility scores over recent analyses.

    Args:
        recent_analyses: List of analysis documents (newest first).

    Returns:
        Plotly Figure object.
    """
    if not recent_analyses:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor=CHART_PAPER_BG,
            plot_bgcolor=CHART_PLOT_BG,
            font_color="#e0e0e0",
            height=250,
        )
        return fig

    docs = list(reversed(recent_analyses))  # oldest → newest
    titles = [d.get("article_title", "Article")[:25] + "…" for d in docs]
    scores = [d.get("credibility_score", 0) for d in docs]
    verdicts = [d.get("verdict", "") for d in docs]
    point_colors = [score_color(s) for s in scores]

    fig = go.Figure(
        go.Scatter(
            x=list(range(len(docs))),
            y=scores,
            mode="lines+markers",
            line=dict(color="#7c6af7", width=2.5),
            marker=dict(color=point_colors, size=10, line=dict(color="#1a1a2e", width=2)),
            text=[f"{t}<br>Score: {s}<br>{v}" for t, s, v in zip(titles, scores, verdicts)],
            hoverinfo="text",
        )
    )
    fig.update_layout(
        paper_bgcolor=CHART_PAPER_BG,
        plot_bgcolor=CHART_PLOT_BG,
        font_color="#e0e0e0",
        height=250,
        xaxis=dict(
            showticklabels=False,
            gridcolor="rgba(255,255,255,0.05)",
            title="Recent Analyses (oldest → newest)",
        ),
        yaxis=dict(
            range=[0, 105],
            gridcolor="rgba(255,255,255,0.07)",
            title="Credibility Score",
        ),
        margin=dict(l=40, r=20, t=20, b=40),
    )
    return fig


def make_history_bar_chart(analyses: list[dict]) -> go.Figure:
    """
    Horizontal bar chart of credibility scores for the history view.

    Args:
        analyses: List of analysis documents.

    Returns:
        Plotly Figure object.
    """
    if not analyses:
        return go.Figure()

    df = pd.DataFrame(
        [
            {
                "title": d.get("article_title", "Article")[:35],
                "score": d.get("credibility_score", 0),
                "verdict": d.get("verdict", ""),
            }
            for d in analyses[:20]  # Cap at 20 for readability
        ]
    )
    df = df.sort_values("score", ascending=True)
    colors = [score_color(int(s)) for s in df["score"]]

    fig = go.Figure(
        go.Bar(
            x=df["score"],
            y=df["title"],
            orientation="h",
            marker=dict(color=colors, line=dict(color="rgba(0,0,0,0.3)", width=1)),
            text=df["score"].astype(str),
            textposition="outside",
            hovertext=df["verdict"],
            hoverinfo="x+y+text",
        )
    )
    fig.update_layout(
        paper_bgcolor=CHART_PAPER_BG,
        plot_bgcolor=CHART_PLOT_BG,
        font_color="#e0e0e0",
        height=max(300, len(df) * 32),
        xaxis=dict(range=[0, 115], title="Credibility Score", gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(title="", tickfont=dict(size=11)),
        margin=dict(l=10, r=50, t=20, b=30),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Export Helpers
# ─────────────────────────────────────────────────────────────────────────────

def flatten_for_export(doc: dict) -> dict:
    """
    Normalize a document for export regardless of its source.

    Handles two shapes:
      1. Live analysis result (from GeminiService) – all fields at top level.
      2. MongoDB document – analysis sub-fields nested under doc['analysis'].

    Returns a flat dict with all fields at the top level so export functions
    always find what they need.
    """
    flat = dict(doc)  # shallow copy

    # If there is a nested 'analysis' dict, merge its keys into the top level
    nested = doc.get("analysis") or {}
    if isinstance(nested, dict):
        for key, value in nested.items():
            # Only fill in if not already present at the top level
            if key not in flat or not flat[key]:
                flat[key] = value

    return flat


# ─────────────────────────────────────────────────────────────────────────────
# Export Functions
# ─────────────────────────────────────────────────────────────────────────────

def export_as_json(analysis: dict) -> bytes:
    """Serialize analysis dict to pretty-printed JSON bytes."""
    flat = flatten_for_export(analysis)
    exportable = {k: v for k, v in flat.items() if k != "_id"}
    return json.dumps(exportable, indent=2, default=str, ensure_ascii=False).encode("utf-8")


def export_as_txt(analysis: dict) -> bytes:
    """Format analysis as a plain-text report."""
    analysis = flatten_for_export(analysis)  # handle nested MongoDB docs
    lines = [
        "=" * 60,
        f"  FAKE NEWS ANALYSIS REPORT",
        f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 60,
        "",
        f"ARTICLE TITLE : {analysis.get('article_title', 'N/A')}",
        f"SOURCE URL    : {analysis.get('source_url', 'N/A') or 'Manual Input'}",
        f"VERDICT       : {analysis.get('verdict', 'N/A')}",
        f"CREDIBILITY   : {analysis.get('credibility_score', 0)}/100",
        f"CONFIDENCE    : {analysis.get('confidence_score', 0)}/100",
        "",
        "─" * 60,
        "SUMMARY",
        "─" * 60,
        analysis.get("summary", ""),
        "",
        "─" * 60,
        "DETAILED EXPLANATION",
        "─" * 60,
        analysis.get("detailed_explanation", ""),
        "",
        "─" * 60,
        "KEY CLAIMS",
        "─" * 60,
    ]
    for i, claim in enumerate(analysis.get("key_claims", []), 1):
        lines.append(f"  {i}. {claim}")

    lines += [
        "",
        "─" * 60,
        "RED FLAGS",
        "─" * 60,
    ]
    red_flags = analysis.get("red_flags", [])
    if red_flags:
        for flag in red_flags:
            lines.append(f"  ⚠ {flag}")
    else:
        lines.append("  None detected.")

    lines += [
        "",
        "─" * 60,
        "TRUST INDICATORS",
        "─" * 60,
    ]
    trust = analysis.get("trust_indicators", [])
    if trust:
        for t in trust:
            lines.append(f"  ✓ {t}")
    else:
        lines.append("  None identified.")

    lines += [
        "",
        "─" * 60,
        "FACT-CHECKING SUGGESTIONS",
        "─" * 60,
    ]
    for i, tip in enumerate(analysis.get("fact_checking_suggestions", []), 1):
        lines.append(f"  {i}. {tip}")

    lines += [
        "",
        "─" * 60,
        "ADDITIONAL INFO",
        "─" * 60,
        f"Bias Indicators        : {analysis.get('bias_indicators', 'N/A')}",
        f"Emotional Language (0-10): {analysis.get('emotional_language_score', 'N/A')}",
        f"Source Notes           : {analysis.get('source_credibility_notes', 'N/A')}",
        f"Missing Context        : {analysis.get('missing_context', 'N/A')}",
        "",
        "=" * 60,
        "  Powered by Google Gemini · Fake News Detector v1.0",
        "=" * 60,
    ]
    return "\n".join(lines).encode("utf-8")


def export_as_pdf(analysis: dict) -> bytes:
    """
    Generate a styled PDF report using ReportLab.

    Returns:
        PDF bytes buffer.
    """
    analysis = flatten_for_export(analysis)  # handle nested MongoDB docs
    try:
        from reportlab.lib import colors as rl_colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            HRFlowable,
            Table,
            TableStyle,
        )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        style_normal = styles["Normal"]
        style_normal.fontName = "Helvetica"
        style_normal.fontSize = 10
        style_normal.leading = 14

        style_heading = ParagraphStyle(
            "MyHeading",
            parent=styles["Heading2"],
            textColor=rl_colors.HexColor("#3a3af4"),
            spaceBefore=12,
            spaceAfter=4,
        )

        story = []

        # ── Title ─────────────────────────────────────────────────────────────
        story.append(
            Paragraph(
                "🔍 Fake News Analysis Report",
                ParagraphStyle(
                    "Title",
                    parent=styles["Title"],
                    textColor=rl_colors.HexColor("#3a3af4"),
                    fontSize=22,
                    spaceAfter=6,
                ),
            )
        )
        story.append(
            Paragraph(
                f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}",
                ParagraphStyle("Sub", parent=style_normal, textColor=rl_colors.grey),
            )
        )
        story.append(Spacer(1, 0.4 * cm))
        story.append(HRFlowable(width="100%", thickness=1, color=rl_colors.HexColor("#3a3af4")))
        story.append(Spacer(1, 0.3 * cm))

        # ── Score Table ────────────────────────────────────────────────────────
        verdict = analysis.get("verdict", "Unknown")
        verdict_colors = {
            "Likely Real": "#00c896",
            "Suspicious": "#f5a623",
            "Likely Fake": "#ff4757",
        }
        v_color = rl_colors.HexColor(verdict_colors.get(verdict, "#888888"))

        score_data = [
            ["Article", analysis.get("article_title", "N/A")],
            ["Source", analysis.get("source_url", "Manual Input") or "Manual Input"],
            ["Verdict", verdict],
            ["Credibility Score", f"{analysis.get('credibility_score', 0)}/100"],
            ["Confidence Score", f"{analysis.get('confidence_score', 0)}/100"],
        ]
        tbl = Table(score_data, colWidths=[4 * cm, 13 * cm])
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), rl_colors.HexColor("#f0f0ff")),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("TEXTCOLOR", (1, 2), (1, 2), v_color),
                    ("FONTNAME", (1, 2), (1, 2), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.lightgrey),
                    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [rl_colors.white, rl_colors.HexColor("#f9f9ff")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(tbl)
        story.append(Spacer(1, 0.4 * cm))

        def section(title: str, content: str | list):
            story.append(Paragraph(title, style_heading))
            if isinstance(content, list):
                for item in content:
                    story.append(Paragraph(f"• {item}", style_normal))
            else:
                story.append(Paragraph(str(content), style_normal))
            story.append(Spacer(1, 0.2 * cm))

        section("Summary", analysis.get("summary", ""))
        section("Detailed Explanation", analysis.get("detailed_explanation", ""))
        section("Key Claims", analysis.get("key_claims", []))
        section("Red Flags", analysis.get("red_flags", []) or ["None detected."])
        section("Trust Indicators", analysis.get("trust_indicators", []) or ["None identified."])
        section("Fact-Checking Suggestions", analysis.get("fact_checking_suggestions", []))

        story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.grey))
        story.append(
            Paragraph(
                f"Bias: {analysis.get('bias_indicators', 'N/A')} | "
                f"Emotional Score: {analysis.get('emotional_language_score', 'N/A')}/10 | "
                f"Source: {analysis.get('source_credibility_notes', 'N/A')}",
                ParagraphStyle("Footer", parent=style_normal, textColor=rl_colors.grey, fontSize=8),
            )
        )

        doc.build(story)
        return buffer.getvalue()

    except ImportError:
        logger.warning("reportlab not installed; falling back to TXT export.")
        return export_as_txt(analysis)
    except Exception as exc:
        logger.error("PDF generation failed: %s", exc)
        return export_as_txt(analysis)


# ─────────────────────────────────────────────────────────────────────────────
# Formatting Helpers for Streamlit
# ─────────────────────────────────────────────────────────────────────────────

def format_timestamp(iso_str: str) -> str:
    """Convert ISO timestamp to human-readable format."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y · %H:%M")
    except Exception:
        return iso_str or "—"


def truncate(text: str, length: int = 120) -> str:
    """Truncate a string for display."""
    return text[:length] + "…" if len(text) > length else text
