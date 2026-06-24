"""
app.py - Main Streamlit Application
=====================================
Entry point for the Fake News Detector.
"""

from __future__ import annotations

import streamlit as st
import sys
import os

# ─── Path Setup ──────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from config import config
from database import MongoDB
from analyzer import analyze_from_text, analyze_from_url
from utils import (
    get_verdict_config, score_color,
    make_gauge_chart, make_verdict_pie, make_trend_chart,
    export_as_json, export_as_txt, export_as_pdf,
    format_timestamp, truncate,
)

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Fake News Detector",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Base ── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.stApp { background: linear-gradient(135deg, #0d0d1a 0%, #1a1a2e 50%, #16213e 100%); }
.main .block-container { padding: 1.5rem 2rem 2rem; max-width: 1300px; }

/* ── Header ── */
.app-header {
    background: linear-gradient(135deg, #3a3af4 0%, #7c6af7 50%, #c548f5 100%);
    border-radius: 20px;
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
    box-shadow: 0 8px 32px rgba(124,106,247,0.3);
    position: relative; overflow: hidden;
}
.app-header::before {
    content: '';
    position: absolute; top: -50%; right: -20%;
    width: 400px; height: 400px;
    background: rgba(255,255,255,0.05);
    border-radius: 50%;
}
.app-header h1 { color: white; font-size: 2.4rem; font-weight: 800; margin: 0; }
.app-header p  { color: rgba(255,255,255,0.85); font-size: 1.05rem; margin: 0.3rem 0 0; }

/* ── Cards ── */
.glass-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 1.5rem;
    backdrop-filter: blur(10px);
    margin-bottom: 1rem;
    transition: transform 0.2s, box-shadow 0.2s;
}
.glass-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }

/* ── Metric Cards ── */
.metric-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    text-align: center;
}
.metric-card .metric-value { font-size: 2rem; font-weight: 800; margin: 0; }
.metric-card .metric-label { color: #aaa; font-size: 0.82rem; margin-top: 0.2rem; text-transform: uppercase; letter-spacing: 0.05em; }

/* ── Verdict Badge ── */
.verdict-badge {
    display: inline-flex; align-items: center; gap: 0.5rem;
    padding: 0.6rem 1.4rem;
    border-radius: 50px;
    font-size: 1.15rem; font-weight: 700;
}

/* ── Section Title ── */
.section-title {
    color: #e0e0e0; font-size: 1rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.08em;
    margin-bottom: 0.8rem; padding-bottom: 0.4rem;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

/* ── Tag Pills ── */
.tag { display: inline-block; padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.82rem; margin: 0.2rem; font-weight: 500; }
.tag-red   { background: rgba(255,71,87,0.18);   color: #ff6b7a; border: 1px solid rgba(255,71,87,0.3); }
.tag-green { background: rgba(0,200,150,0.18);   color: #00e5a8; border: 1px solid rgba(0,200,150,0.3); }
.tag-blue  { background: rgba(58,58,244,0.18);   color: #8080ff; border: 1px solid rgba(58,58,244,0.3); }
.tag-gold  { background: rgba(245,166,35,0.18);  color: #ffc15e; border: 1px solid rgba(245,166,35,0.3); }

/* ── Inputs – broad selectors for Streamlit 1.35+ ── */
input, textarea, [data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
.stTextInput input, .stTextArea textarea {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 12px !important;
    color: #f0f0f0 !important;
    caret-color: #f0f0f0 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
}
input::placeholder, textarea::placeholder {
    color: rgba(200,200,200,0.45) !important;
}
input:focus, textarea:focus {
    border-color: #7c6af7 !important;
    box-shadow: 0 0 0 2px rgba(124,106,247,0.3) !important;
    outline: none !important;
}
/* Label text above inputs */
.stTextInput label, .stTextArea label,
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label {
    color: #c8c8e8 !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
}
/* Selectbox text */
[data-baseweb="select"] *, .stSelectbox * {
    color: #f0f0f0 !important;
}
[data-baseweb="select"] [data-baseweb="icon"] { color: #aaa !important; }
/* General body text */
.stMarkdown, .stMarkdown p, p, li, span:not([class]) {
    color: #d8d8e8;
}
/* Caption / help text */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #9090aa !important;
}
/* Metric label + value */
[data-testid="stMetricLabel"] { color: #b0b0cc !important; }
[data-testid="stMetricValue"] { color: #f0f0f0 !important; }

/* ── Buttons ── */
.stButton>button {
    background: linear-gradient(135deg, #3a3af4, #7c6af7) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.6rem 2rem !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
    box-shadow: 0 4px 15px rgba(124,106,247,0.3) !important;
}
.stButton>button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(124,106,247,0.45) !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(13,13,26,0.95) !important;
    border-right: 1px solid rgba(255,255,255,0.08) !important;
}
[data-testid="stSidebar"] .stMarkdown { color: #ccc; }

/* ── Status Pills ── */
.status-connected { color: #00c896; font-weight: 600; }
.status-disconnected { color: #ff4757; font-weight: 600; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { background: rgba(255,255,255,0.04); border-radius: 12px; padding: 4px; }
.stTabs [data-baseweb="tab"] { border-radius: 10px; color: #aaa; font-weight: 500; }
.stTabs [aria-selected="true"] { background: rgba(124,106,247,0.3) !important; color: #e0e0e0 !important; }

/* ── Expander ── */
.streamlit-expanderHeader { color: #c0c0c0 !important; font-weight: 500; }
details[open] .streamlit-expanderHeader { color: #e0e0e0 !important; }

/* ── Divider ── */
hr { border-color: rgba(255,255,255,0.08) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,0.03); }
::-webkit-scrollbar-thumb { background: rgba(124,106,247,0.5); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Session State Init
# ─────────────────────────────────────────────────────────────────────────────
def _init_session():
    defaults = {
        "analysis_result": None,
        "analyzing": False,
        "db_connected": False,
        "input_mode": "Text Input",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_session()


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style='text-align:center; padding: 1rem 0 0.5rem;'>
            <div style='font-size:2.5rem;'>🔍</div>
            <div style='color:#7c6af7; font-weight:700; font-size:1.1rem;'>Fake News Detector</div>
            <div style='color:#666; font-size:0.75rem;'>v1.0 · Powered by Gemini 2.5</div>
        </div>
        <hr style='margin: 0.8rem 0;'>
        """, unsafe_allow_html=True)

        # ── DB Status ─────────────────────────────────────────────────────────
        st.markdown("**Database Status**")
        if st.button("🔄 Test Connection", key="btn_test_conn"):
            with st.spinner("Connecting…"):
                connected = MongoDB.connect()
                st.session_state.db_connected = connected

        if st.session_state.db_connected:
            st.markdown('<p class="status-connected">● MongoDB Connected</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="status-disconnected">● MongoDB Disconnected</p>', unsafe_allow_html=True)
            st.caption("Add MONGODB_URI to .env and click 'Test Connection'")

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Config Check ──────────────────────────────────────────────────────
        missing = config.validate()
        if missing:
            st.warning(f"⚠️ Missing: `{'`, `'.join(missing)}`\nCheck your `.env` file.")
        else:
            st.success("✅ All API keys configured")

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Navigation ────────────────────────────────────────────────────────
        st.markdown("**Navigation**")
        st.page_link("app.py", label="🏠 Analyze Article", icon=None)
        st.page_link("pages/History.py", label="📋 History & Dashboard", icon=None)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("""
        <div style='color:#555; font-size:0.72rem; text-align:center;'>
        Built with Streamlit + Gemini 2.5 Flash<br>MongoDB Atlas · Plotly
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
def render_header():
    st.markdown("""
    <div class="app-header">
        <h1>🔍 Fake News Detector</h1>
        <p>AI-powered credibility analysis for students · Analyze articles in seconds</p>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Input Section
# ─────────────────────────────────────────────────────────────────────────────
def render_input_section() -> dict | None:
    """Render input tabs and return an analysis result (or None)."""
    tab_text, tab_url = st.tabs(["✏️  Paste Article Text", "🌐  Analyze from URL"])
    result = None

    # ── Text Tab ──────────────────────────────────────────────────────────────
    with tab_text:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            title = st.text_input(
                "Article Title (optional)",
                placeholder="Enter the article headline…",
                key="txt_title",
            )
            text = st.text_area(
                "Article Text *",
                placeholder="Paste the full article text here…",
                height=220,
                key="txt_body",
            )
            col1, col2 = st.columns([3, 1])
            with col1:
                char_count = len(text)
                if char_count > 0:
                    st.caption(f"📝 {char_count:,} characters · ~{char_count // 5:,} words")
            with col2:
                analyze_text_btn = st.button("🔍 Analyze", key="btn_analyze_text", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            if analyze_text_btn:
                if not text.strip():
                    st.error("Please paste article text before analyzing.")
                else:
                    with st.spinner("🤖 Analyzing with Gemini 2.5 Flash…"):
                        result = analyze_from_text(title=title, text=text)

    # ── URL Tab ───────────────────────────────────────────────────────────────
    with tab_url:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            url = st.text_input(
                "Article URL *",
                placeholder="https://example.com/news-article",
                key="url_input",
            )
            st.caption("🔗 Supports most news websites. Some paywalled sites may not work.")

            col1, col2 = st.columns([3, 1])
            with col2:
                analyze_url_btn = st.button("🔍 Analyze URL", key="btn_analyze_url", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            if analyze_url_btn:
                if not url.strip():
                    st.error("Please enter a URL before analyzing.")
                else:
                    with st.spinner("🌐 Scraping article… ✨ Analyzing with Gemini…"):
                        result = analyze_from_url(url=url)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Results Section
# ─────────────────────────────────────────────────────────────────────────────
def render_results(r: dict):
    """Render a complete analysis result."""
    if not r.get("success"):
        st.error(f"❌ Analysis failed: {r.get('error', 'Unknown error')}")
        return

    verdict = r.get("verdict", "Unknown")
    vc = get_verdict_config(verdict)
    cred = r.get("credibility_score", 0)
    conf = r.get("confidence_score", 0)

    st.markdown("---")
    st.markdown("## 📊 Analysis Results")

    # ── Row 1: Verdict + Scores ───────────────────────────────────────────────
    col_verdict, col_gauge, col_conf = st.columns([2, 2, 2])

    with col_verdict:
        st.markdown(f"""
        <div class="glass-card" style="border-left: 4px solid {vc['color']}; text-align:center; padding: 2rem 1rem;">
            <div style="font-size: 3rem; margin-bottom:0.3rem">{vc['icon']}</div>
            <div class="verdict-badge" style="background:{vc['bg']}; color:{vc['color']}; margin: 0 auto;">
                {verdict}
            </div>
            <div style="color:#aaa; font-size:0.82rem; margin-top:0.8rem;">AI Verdict</div>
        </div>
        """, unsafe_allow_html=True)

    with col_gauge:
        st.plotly_chart(
            make_gauge_chart(cred, "Credibility Score"),
            use_container_width=True,
            key="gauge_cred",
        )

    with col_conf:
        st.plotly_chart(
            make_gauge_chart(conf, "Confidence Score"),
            use_container_width=True,
            key="gauge_conf",
        )

    # ── Article Info ──────────────────────────────────────────────────────────
    if r.get("article_title") or r.get("source_url"):
        st.markdown(f"""
        <div class="glass-card" style="padding: 1rem 1.5rem;">
            <span style="color:#7c6af7; font-weight:600;">📰 {r.get('article_title', 'Article')}</span>
            {"&nbsp;&nbsp;·&nbsp;&nbsp;<a href='" + r.get('source_url','') + "' target='_blank' style='color:#aaa; font-size:0.82rem;'>View Source</a>" if r.get('source_url') else ''}
        </div>
        """, unsafe_allow_html=True)

    # ── Summary ───────────────────────────────────────────────────────────────
    st.markdown('<p class="section-title">📝 Student-Friendly Summary</p>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="glass-card">
        <p style="color:#d0d0d0; line-height:1.7; margin:0;">{r.get('summary', '')}</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Claims, Red Flags, Trust ───────────────────────────────────────────────
    col_claims, col_flags, col_trust = st.columns(3)

    with col_claims:
        st.markdown('<p class="section-title">🔑 Key Claims</p>', unsafe_allow_html=True)
        claims = r.get("key_claims", [])
        if claims:
            tags = "".join(f'<span class="tag tag-blue">{c[:70]}</span>' for c in claims)
            st.markdown(f'<div class="glass-card">{tags}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="glass-card"><em style="color:#666;">None identified</em></div>', unsafe_allow_html=True)

    with col_flags:
        st.markdown('<p class="section-title">🚩 Red Flags</p>', unsafe_allow_html=True)
        flags = r.get("red_flags", [])
        if flags:
            tags = "".join(f'<span class="tag tag-red">⚠ {f[:70]}</span>' for f in flags)
            st.markdown(f'<div class="glass-card">{tags}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="glass-card"><span class="tag tag-green">✓ No red flags</span></div>', unsafe_allow_html=True)

    with col_trust:
        st.markdown('<p class="section-title">✅ Trust Indicators</p>', unsafe_allow_html=True)
        trust = r.get("trust_indicators", [])
        if trust:
            tags = "".join(f'<span class="tag tag-green">✓ {t[:70]}</span>' for t in trust)
            st.markdown(f'<div class="glass-card">{tags}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="glass-card"><em style="color:#666;">None identified</em></div>', unsafe_allow_html=True)

    # ── Fact-checking Tips ────────────────────────────────────────────────────
    st.markdown('<p class="section-title">💡 Fact-Checking Suggestions</p>', unsafe_allow_html=True)
    suggestions = r.get("fact_checking_suggestions", [])
    if suggestions:
        cols = st.columns(min(len(suggestions), 3))
        for i, (col, tip) in enumerate(zip(cols, suggestions)):
            with col:
                st.markdown(f"""
                <div class="glass-card" style="border-top: 2px solid #7c6af7;">
                    <div style="color:#7c6af7; font-weight:700; font-size:1.1rem; margin-bottom:0.4rem;">Step {i+1}</div>
                    <div style="color:#ccc; font-size:0.88rem; line-height:1.6;">{tip}</div>
                </div>
                """, unsafe_allow_html=True)

    # ── Detailed Explanation ──────────────────────────────────────────────────
    with st.expander("📖 Detailed Expert Explanation", expanded=False):
        st.markdown(f"""
        <div style="color:#d0d0d0; line-height:1.75; font-size:0.95rem; padding: 0.5rem;">
            {r.get('detailed_explanation', '').replace(chr(10), '<br>')}
        </div>
        """, unsafe_allow_html=True)

    # ── Additional Signals ────────────────────────────────────────────────────
    with st.expander("🔬 Additional Analysis Signals", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Emotional Language", f"{r.get('emotional_language_score', 0)}/10")
        with c2:
            st.info(f"**Bias:** {r.get('bias_indicators', 'None detected')}")
        with c3:
            st.warning(f"**Missing Context:** {r.get('missing_context', 'None identified')}")
        st.caption(f"**Source Notes:** {r.get('source_credibility_notes', 'Unknown')}")

    # ── Export ────────────────────────────────────────────────────────────────
    # Use a unique suffix per result (based on title+score) to avoid
    # DuplicateWidgetID errors when results are re-rendered.
    import hashlib
    _uid = hashlib.md5(
        f"{r.get('article_title','')}{r.get('credibility_score',0)}".encode()
    ).hexdigest()[:8]

    st.markdown("---")
    st.markdown("### 📥 Download Report")
    col_pdf, col_txt, col_json = st.columns(3)

    with col_pdf:
        try:
            pdf_bytes = export_as_pdf(r)
            st.download_button("📄 Download PDF", data=pdf_bytes,
                               file_name="analysis_report.pdf", mime="application/pdf",
                               use_container_width=True, key=f"dl_pdf_{_uid}")
        except Exception as e:
            st.error(f"PDF export failed: {e}")
    with col_txt:
        try:
            txt_bytes = export_as_txt(r)
            st.download_button("📝 Download TXT", data=txt_bytes,
                               file_name="analysis_report.txt", mime="text/plain",
                               use_container_width=True, key=f"dl_txt_{_uid}")
        except Exception as e:
            st.error(f"TXT export failed: {e}")
    with col_json:
        try:
            json_bytes = export_as_json(r)
            st.download_button("📊 Download JSON", data=json_bytes,
                               file_name="analysis_report.json", mime="application/json",
                               use_container_width=True, key=f"dl_json_{_uid}")
        except Exception as e:
            st.error(f"JSON export failed: {e}")

    # Storage notice
    if r.get("doc_id"):
        st.success(f"💾 Saved to MongoDB · ID: `{r['doc_id']}`")
    elif not MongoDB.is_connected():
        st.info("ℹ️ Connect MongoDB to save analyses for history & dashboard.")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    render_sidebar()
    render_header()

    # Try to auto-connect DB on first load
    if not st.session_state.db_connected and config.MONGODB_URI:
        st.session_state.db_connected = MongoDB.connect()

    result = render_input_section()

    if result is not None:
        st.session_state.analysis_result = result

    if st.session_state.analysis_result:
        render_results(st.session_state.analysis_result)


if __name__ == "__main__":
    main()
