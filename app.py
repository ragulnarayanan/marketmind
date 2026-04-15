"""
MarketMind — Streamlit entry point.
Handles auth gate, Qdrant collection init, and sidebar navigation.
"""
import os

import streamlit as st

st.set_page_config(
    page_title="MarketMind",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global theme CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Reset & Base ─────────────────────────────────────────────── */
*, *::before, *::after {
    box-sizing: border-box;
    text-transform: none !important;
}

.stApp, .main, [data-testid="stAppViewContainer"] {
    background: #000000 !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Hide auto-generated Streamlit nav (prevents duplicate menu) ─ */
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Sidebar ──────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #0a0a0a !important;
    border-right: 1px solid #1a1a1a !important;
}

/* ── Headings ─────────────────────────────────────────────────── */
h1 {
    font-family: 'Inter', sans-serif !important;
    font-size: 28px !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    letter-spacing: -0.02em !important;
    text-transform: none !important;
}
h2 {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    color: #76b900 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid rgba(118,185,0,0.2) !important;
    padding-bottom: 8px !important;
    margin-bottom: 16px !important;
}
h3 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    color: #ffffff !important;
    text-transform: none !important;
}
h4 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    color: #ffffff !important;
}
p, span, div, label, li {
    font-family: 'Inter', sans-serif !important;
    color: #a1a1aa;
}

/* ── Metric cards ─────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 10px !important;
    padding: 16px 20px !important;
    transition: border-color 0.2s ease, background 0.2s ease !important;
}
[data-testid="stMetric"]:hover {
    border-color: #76b900 !important;
    background: rgba(118,185,0,0.04) !important;
}
[data-testid="stMetricLabel"] {
    font-size: 12px !important;
    font-weight: 500 !important;
    color: #52525b !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
[data-testid="stMetricValue"] {
    font-size: 24px !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    letter-spacing: -0.02em !important;
}
[data-testid="stMetricDelta"] {
    font-size: 13px !important;
    font-weight: 500 !important;
}
[data-testid="stMetricDelta"][data-direction="up"]   { color: #76b900 !important; }
[data-testid="stMetricDelta"][data-direction="down"]  { color: #ef4444 !important; }

/* ── Buttons ──────────────────────────────────────────────────── */
.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    background: transparent !important;
    color: #76b900 !important;
    border: 1.5px solid #76b900 !important;
    border-radius: 8px !important;
    padding: 10px 24px !important;
    transition: background 0.2s ease, transform 0.1s ease,
                box-shadow 0.2s ease !important;
    text-transform: none !important;
}
.stButton > button:hover {
    background: rgba(118,185,0,0.08) !important;
    box-shadow: 0 0 16px rgba(118,185,0,0.25) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
    background: rgba(118,185,0,0.15) !important;
}
.stButton > button[kind="primary"] {
    background: #76b900 !important;
    color: #000000 !important;
    border: none !important;
}
.stButton > button[kind="primary"]:hover {
    background: #5a8c00 !important;
    box-shadow: 0 0 16px rgba(118,185,0,0.3) !important;
}

/* ── Text inputs ──────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
textarea {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    background: #0a0a0a !important;
    color: #ffffff !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 8px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
textarea:focus {
    border-color: #76b900 !important;
    box-shadow: 0 0 0 3px rgba(118,185,0,0.12) !important;
    outline: none !important;
}

/* ── Selectbox ────────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 8px !important;
    color: #ffffff !important;
}

/* ── DataFrames / Tables ──────────────────────────────────────── */
[data-testid="stDataFrame"], .stDataFrame {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 10px !important;
}
[data-testid="stDataFrame"] th {
    background: #111111 !important;
    color: #52525b !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    border-bottom: 1px solid #1a1a1a !important;
}
[data-testid="stDataFrame"] td {
    color: #ffffff !important;
    font-size: 14px !important;
    border-bottom: 1px solid #0f0f0f !important;
}

/* ── Expanders ────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"]:hover {
    border-color: #76b900 !important;
}
[data-testid="stExpander"] summary {
    color: #ffffff !important;
    font-weight: 500 !important;
}

/* ── Dividers ─────────────────────────────────────────────────── */
hr {
    border: none !important;
    border-top: 1px solid #76b900 !important;
    opacity: 0.3 !important;
    margin: 24px 0 !important;
}

/* ── Scrollbar ────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #000000; }
::-webkit-scrollbar-thumb {
    background: #76b900;
    border-radius: 2px;
}
::-webkit-scrollbar-thumb:hover { background: #5a8c00; }

/* ── Status / spinner ─────────────────────────────────────────── */
[data-testid="stStatusWidget"] {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 10px !important;
}

/* ── Alerts / info boxes ──────────────────────────────────────── */
[data-testid="stAlert"] {
    background: #0a0a0a !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Caption / small text ─────────────────────────────────────── */
[data-testid="stCaptionContainer"] {
    color: #52525b !important;
    font-size: 12px !important;
}

/* ── Tabs ─────────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    background: #0a0a0a !important;
    border-bottom: 1px solid #1a1a1a !important;
    gap: 0 !important;
}
[data-testid="stTabs"] [role="tab"] {
    color: #52525b !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 10px 20px !important;
    border-bottom: 2px solid transparent !important;
    transition: color 0.15s ease !important;
    text-transform: none !important;
}
[data-testid="stTabs"] [role="tab"]:hover {
    color: #ffffff !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: #76b900 !important;
    border-bottom: 2px solid #76b900 !important;
    background: transparent !important;
}
</style>
""", unsafe_allow_html=True)

# ── Qdrant collection bootstrap (once per session) ────────────────────────────
if not st.session_state.get("_qdrant_init"):
    try:
        from data.qdrant_client import init_collections
        init_collections()
        st.session_state["_qdrant_init"] = True
    except Exception as e:
        st.warning(f"Qdrant unavailable — vector search disabled. ({e})")
        st.session_state["_qdrant_init"] = False

# ── Auth gate ──────────────────────────────────────────────────────────────────
TEST_UID = os.getenv("TEST_UID")

if TEST_UID and not st.session_state.get("uid"):
    st.session_state["uid"]          = TEST_UID
    st.session_state["display_name"] = "Dev User"
    st.session_state["email"]        = "dev@example.com"
    try:
        from data.firestore_client import get_or_create_user
        get_or_create_user(TEST_UID, "dev@example.com", "Dev User")
    except Exception:
        pass

if not st.session_state.get("uid"):
    st.title("MarketMind")
    st.markdown("### AI-powered stock research and daily portfolio brief")
    st.divider()

    st.markdown("<h2 style='color:#76b900;border-bottom:1px solid rgba(118,185,0,0.2);padding-bottom:8px;font-family:Inter,sans-serif;letter-spacing:0.06em;text-transform:uppercase;font-size:14px'>Sign In</h2>", unsafe_allow_html=True)
    with st.form("login_form"):
        user_id      = st.text_input("User ID", placeholder="your-unique-id")
        display_name = st.text_input("Display Name", placeholder="Jane Smith")
        email        = st.text_input("Email", placeholder="you@example.com")
        submitted    = st.form_submit_button("Sign In", type="primary")

        if submitted:
            if not user_id or not email:
                st.error("User ID and email are required.")
            else:
                try:
                    from data.firestore_client import get_or_create_user
                    get_or_create_user(user_id, email, display_name or "User")
                    st.session_state["uid"]          = user_id
                    st.session_state["display_name"] = display_name or "User"
                    st.session_state["email"]        = email
                    st.rerun()
                except Exception as e:
                    st.error(f"Sign-in failed: {e}")
    st.info("For local dev, set TEST_UID in your .env file to skip the login form.")
    st.stop()

# ── Main page (authenticated) ──────────────────────────────────────────────────
uid          = st.session_state["uid"]
display_name = st.session_state.get("display_name", "User")

with st.sidebar:
    st.markdown(
        "<div style='padding:20px 12px 8px'>"
        "<span style='color:#76b900;font-size:20px;font-weight:700;"
        "font-family:Inter,sans-serif;letter-spacing:-0.02em'>"
        "MarketMind</span></div>",
        unsafe_allow_html=True,
    )

    _nav = [
        ("Home",           "/"),
        ("Daily Brief",    "/daily_brief"),
        ("Stock Research", "/stock_research"),
        ("Portfolio",      "/portfolio"),
        ("Watchlist",      "/watchlist"),
    ]
    _current = st.query_params.get("page", "/")
    for _label, _path in _nav:
        _active = (_path == "/" and _current == "/") or \
                  (_path != "/" and _path in str(_current))
        _style = (
            "color:#76b900 !important;background:rgba(118,185,0,0.08);"
            "border-left:2px solid #76b900;padding-left:10px;"
        ) if _active else "color:#a1a1aa;"
        st.markdown(
            f"<a href='{_path}' style='display:block;padding:9px 12px;"
            f"border-radius:6px;text-decoration:none;"
            f"font-family:Inter,sans-serif;font-size:14px;"
            f"font-weight:500;{_style}'>{_label}</a>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='height:1px;background:#1a1a1a;margin:14px 8px'></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='padding:4px 12px 8px'>"
        f"<span style='color:#ffffff;font-size:13px;font-weight:500;"
        f"font-family:Inter,sans-serif'>{display_name}</span><br>"
        f"<span style='color:#52525b;font-size:12px;"
        f"font-family:Inter,sans-serif'>"
        f"{st.session_state.get('email', '')}</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("Sign Out"):
        for key in ["uid", "display_name", "email"]:
            st.session_state.pop(key, None)
        st.rerun()

st.title("MarketMind")
st.markdown("Welcome back, **{}**. Use the sidebar to navigate.".format(display_name))
st.divider()

col1, col2 = st.columns(2)
with col1:
    st.markdown("### Daily Brief")
    st.write("Get your personalized portfolio P&L, news summaries, macro alerts, and buy/wait signals.")
    st.markdown(
        "<a href='/daily_brief' style='display:inline-block;margin-top:8px;"
        "padding:9px 20px;background:#76b900;color:#000000;font-weight:600;"
        "font-size:14px;border-radius:8px;text-decoration:none;"
        "font-family:Inter,sans-serif'>Open Daily Brief</a>",
        unsafe_allow_html=True,
    )

with col2:
    st.markdown("### Stock Research")
    st.write("Enter any ticker for a five-agent deep dive: news, SEC filings, financials, and a Buy/Hold/Sell verdict.")
    st.markdown(
        "<a href='/stock_research' style='display:inline-block;margin-top:8px;"
        "padding:9px 20px;background:#76b900;color:#000000;font-weight:600;"
        "font-size:14px;border-radius:8px;text-decoration:none;"
        "font-family:Inter,sans-serif'>Open Research</a>",
        unsafe_allow_html=True,
    )
