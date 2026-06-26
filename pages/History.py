"""
pages/History.py - History & Dashboard Page
=============================================
Streamlit multi-page: analysis history, stats, charts, search/filter, delete.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st

from database import MongoDB
from services.mongo_service import MongoService
from utils import (
    get_verdict_config, score_color,
    make_verdict_pie, make_trend_chart, make_history_bar_chart,
    export_as_json, export_as_txt, export_as_pdf,
    flatten_for_export,
    format_timestamp, truncate,
)
from config import config

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="History & Dashboard · Fake News Detector",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS (reuse same theme) ───────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.stApp { background: linear-gradient(135deg, #0d0d1a 0%, #1a1a2e 50%, #16213e 100%); }
.main .block-container { padding: 1.5rem 2rem 2rem; max-width: 1300px; }
.glass-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px; padding: 1.4rem;
    backdrop-filter: blur(10px); margin-bottom: 1rem;
    transition: transform 0.2s, box-shadow 0.2s;
}
.glass-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
.section-title {
    color: #e0e0e0; font-size: 0.9rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.08em;
    margin-bottom: 0.8rem; padding-bottom: 0.4rem;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}
.metric-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 14px; padding: 1.2rem 1.4rem; text-align: center;
}
.metric-card .metric-value { font-size: 2.2rem; font-weight: 800; margin: 0; }
.metric-card .metric-label { color: #aaa; font-size: 0.8rem; margin-top: 0.2rem; text-transform: uppercase; letter-spacing: 0.05em; }
.history-row {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px; padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
    transition: all 0.2s;
}
.history-row:hover { border-color: rgba(124,106,247,0.3); background: rgba(124,106,247,0.06); }
.tag { display: inline-block; padding: 0.25rem 0.7rem; border-radius: 20px; font-size: 0.78rem; margin: 0.15rem; font-weight: 500; }
.tag-real  { background: rgba(0,200,150,0.18); color: #00e5a8; border: 1px solid rgba(0,200,150,0.3); }
.tag-fake  { background: rgba(255,71,87,0.18); color: #ff6b7a; border: 1px solid rgba(255,71,87,0.3); }
.tag-susp  { background: rgba(245,166,35,0.18); color: #ffc15e; border: 1px solid rgba(245,166,35,0.3); }
.stButton>button {
    background: linear-gradient(135deg,#3a3af4,#7c6af7) !important;
    color: white !important; border: none !important;
    border-radius: 10px !important; font-weight: 600 !important;
    transition: all 0.2s !important;
}
.stButton>button:hover { transform: translateY(-1px) !important; }
[data-testid="stSidebar"] { background: rgba(13,13,26,0.95) !important; border-right: 1px solid rgba(255,255,255,0.08) !important; }
/* Inputs – broad selectors for Streamlit 1.35+ */
input, textarea, [data-baseweb="input"] input, .stTextInput input {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 10px !important;
    color: #f0f0f0 !important;
    caret-color: #f0f0f0 !important;
}
input::placeholder { color: rgba(200,200,200,0.45) !important; }
[data-baseweb="select"] *, .stSelectbox * { color: #f0f0f0 !important; }
hr { border-color: rgba(255,255,255,0.08) !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style='text-align:center; padding: 1rem 0 0.5rem;'>
            <div style='font-size:2.5rem;'>📋</div>
            <div style='color:#7c6af7; font-weight:700; font-size:1.1rem;'>History & Dashboard</div>
        </div>
        <hr>
        """, unsafe_allow_html=True)
        st.page_link("app.py", label="🏠 Back to Analyzer")
        st.page_link("pages/History.py", label="📋 History & Dashboard")
        st.markdown("<hr>", unsafe_allow_html=True)

        if not MongoDB.is_connected() and config.MONGODB_URI:
            MongoDB.connect()

        if MongoDB.is_connected():
            st.markdown('<p style="color:#00c896; font-weight:600;">● MongoDB Connected</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#ff4757; font-weight:600;">● MongoDB Disconnected</p>', unsafe_allow_html=True)
            if st.button("Reconnect", key="btn_reconnect"):
                MongoDB.connect()


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard Stats
# ─────────────────────────────────────────────────────────────────────────────
def render_dashboard_stats(stats: dict):
    total = stats.get("total", 0)
    avg   = stats.get("avg_credibility", 0.0)
    vdict = stats.get("verdict_distribution", {})

    real_n = vdict.get("Likely Real", 0)
    fake_n = vdict.get("Likely Fake", 0)
    susp_n = vdict.get("Suspicious", 0)

    # ── KPI Row ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        (c1, str(total),   "Total Analyzed", "#7c6af7"),
        (c2, f"{avg:.1f}", "Avg Credibility", score_color(int(avg))),
        (c3, str(real_n),  "Likely Real", "#00c896"),
        (c4, str(susp_n),  "Suspicious", "#f5a623"),
        (c5, str(fake_n),  "Likely Fake", "#ff4757"),
    ]
    for col, val, label, color in metrics:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color:{color}">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts Row ────────────────────────────────────────────────────────────
    col_pie, col_trend = st.columns([1, 2])

    with col_pie:
        st.markdown('<p class="section-title">🥧 Verdict Distribution</p>', unsafe_allow_html=True)
        if vdict:
            st.plotly_chart(make_verdict_pie(vdict), use_container_width=True, key="pie_chart")
        else:
            st.info("No data yet. Analyze some articles first!")

    with col_trend:
        st.markdown('<p class="section-title">📈 Recent Credibility Trends</p>', unsafe_allow_html=True)
        recent = stats.get("recent", [])
        if recent:
            st.plotly_chart(make_trend_chart(recent), use_container_width=True, key="trend_chart")
        else:
            st.info("No trend data yet.")


# ─────────────────────────────────────────────────────────────────────────────
# History Table
# ─────────────────────────────────────────────────────────────────────────────
def render_history(analyses: list[dict]):
    if not analyses:
        st.info("📭 No analyses found. Try adjusting filters or analyze some articles!")
        return

    # Bar chart of all visible results
    st.markdown('<p class="section-title">📊 Credibility Scores – All Visible Results</p>', unsafe_allow_html=True)
    st.plotly_chart(make_history_bar_chart(analyses), use_container_width=True, key="history_bar")

    st.markdown(f"**{len(analyses)} result(s) found**", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    for doc in analyses:
        _render_history_row(doc)


def _render_history_row(doc: dict):
    """Render a single collapsible history row."""
    verdict  = doc.get("verdict", "Unknown")
    cred     = doc.get("credibility_score", 0)
    title    = doc.get("article_title", "Untitled")
    ts       = format_timestamp(doc.get("created_at", ""))
    doc_id   = doc.get("_id", "")
    vc       = get_verdict_config(verdict)

    tag_class = {
        "Likely Real": "tag-real",
        "Likely Fake": "tag-fake",
        "Suspicious":  "tag-susp",
    }.get(verdict, "tag-susp")

    with st.container():
        st.markdown(f"""
        <div class="history-row">
            <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:0.5rem;">
                <div style="flex:1; min-width:200px;">
                    <div style="color:#e0e0e0; font-weight:600; font-size:0.95rem;">{truncate(title, 80)}</div>
                    <div style="color:#666; font-size:0.78rem; margin-top:0.2rem;">{ts}</div>
                </div>
                <div style="display:flex; align-items:center; gap:0.8rem;">
                    <span class="tag {tag_class}">{vc['icon']} {verdict}</span>
                    <span style="color:{score_color(cred)}; font-weight:700; font-size:1rem;">{cred}/100</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"🔍 View Full Report – {truncate(title, 50)}"):
            # ── Summary & Analysis ────────────────────────────────────────────
            st.markdown(f"**📝 Summary:** {doc.get('summary', 'N/A')}")

            analysis = doc.get("analysis", {})
            if analysis:
                col_a, col_b = st.columns(2)
                with col_a:
                    if analysis.get("key_claims"):
                        st.markdown("**🔑 Key Claims**")
                        for c in analysis["key_claims"]:
                            st.markdown(f"- {c}")
                    if analysis.get("red_flags"):
                        st.markdown("**🚩 Red Flags**")
                        for f in analysis["red_flags"]:
                            st.markdown(f"- ⚠ {f}")
                with col_b:
                    if analysis.get("trust_indicators"):
                        st.markdown("**✅ Trust Indicators**")
                        for t in analysis["trust_indicators"]:
                            st.markdown(f"- ✓ {t}")
                    if analysis.get("fact_checking_suggestions"):
                        st.markdown("**💡 Fact-Check Tips**")
                        for s in analysis["fact_checking_suggestions"]:
                            st.markdown(f"- {s}")
                if analysis.get("detailed_explanation"):
                    st.markdown("**📖 Detailed Explanation**")
                    st.markdown(analysis["detailed_explanation"])

            # ── Source info ───────────────────────────────────────────────────
            if doc.get("source_url"):
                st.markdown(f"🔗 [View Original Article]({doc['source_url']})")

            # ── Export & Delete ───────────────────────────────────────────────
            st.markdown("**📥 Export This Report**")
            flat_doc = flatten_for_export(doc)  # merge nested 'analysis' fields
            ec1, ec2, ec3, ec4 = st.columns([1, 1, 1, 1])
            with ec1:
                try:
                    st.download_button(
                        "📄 PDF", data=export_as_pdf(flat_doc),
                        file_name=f"report_{doc_id[:8]}.pdf", mime="application/pdf",
                        key=f"pdf_{doc_id}", use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"PDF error: {e}")
            with ec2:
                try:
                    st.download_button(
                        "📝 TXT", data=export_as_txt(flat_doc),
                        file_name=f"report_{doc_id[:8]}.txt", mime="text/plain",
                        key=f"txt_{doc_id}", use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"TXT error: {e}")
            with ec3:
                try:
                    st.download_button(
                        "📊 JSON", data=export_as_json(flat_doc),
                        file_name=f"report_{doc_id[:8]}.json", mime="application/json",
                        key=f"json_{doc_id}", use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"JSON error: {e}")
            with ec4:
                if st.button("🗑️ Delete", key=f"del_{doc_id}", use_container_width=True):
                    if MongoService.delete_analysis(doc_id):
                        st.success("Deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete.")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    render_sidebar()

    # Header
    st.markdown("""
    <div style="background:linear-gradient(135deg,#16213e,#1a1a2e);border:1px solid rgba(255,255,255,0.1);
                border-radius:20px;padding:1.8rem 2.5rem;margin-bottom:2rem;
                box-shadow:0 8px 32px rgba(0,0,0,0.3);">
        <h1 style="color:#e0e0e0;font-size:2rem;font-weight:800;margin:0;">
            📋 History &amp; Dashboard
        </h1>
        <p style="color:#888;margin:0.3rem 0 0;">Browse past analyses, view statistics, and manage your reports</p>
    </div>
    """, unsafe_allow_html=True)

    if not MongoDB.is_connected():
        st.error("⚠️ MongoDB is not connected. Please configure your `.env` and reconnect from the sidebar.")
        st.stop()

    # ── Load Stats ─────────────────────────────────────────────────────────────
    with st.spinner("Loading dashboard…"):
        stats = MongoService.get_dashboard_stats()

    tab_dash, tab_hist = st.tabs(["📊 Dashboard", "📋 All Analyses"])

    # ── Dashboard Tab ──────────────────────────────────────────────────────────
    with tab_dash:
        render_dashboard_stats(stats)

    # ── History Tab ───────────────────────────────────────────────────────────
    with tab_hist:
        # Search & Filter
        st.markdown('<p class="section-title">🔎 Search & Filter</p>', unsafe_allow_html=True)
        sf_col1, sf_col2, sf_col3 = st.columns([3, 1, 1])
        with sf_col1:
            keyword = st.text_input("Search keyword", placeholder="Enter title, keyword…", key="search_kw", label_visibility="collapsed")
        with sf_col2:
            verdict_filter = st.selectbox("Verdict", ["All", "Likely Real", "Suspicious", "Likely Fake"], key="verdict_filter", label_visibility="collapsed")
        with sf_col3:
            if st.button("🔍 Search", key="btn_search", use_container_width=True):
                st.session_state["search_triggered"] = True

        # Fetch analyses
        if keyword.strip() or verdict_filter != "All":
            analyses = MongoService.search_analyses(keyword=keyword, verdict_filter=verdict_filter)
        else:
            analyses = MongoService.list_analyses(limit=100)

        st.markdown("<br>", unsafe_allow_html=True)
        render_history(analyses)


if __name__ == "__main__":
    main()
