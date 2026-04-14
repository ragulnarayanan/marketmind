"""
MarketMind — Streamlit entry point.
Handles auth gate, Qdrant collection init, and sidebar navigation.
"""
import os

import streamlit as st

st.set_page_config(
    page_title="Home",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global theme CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Reset & Base ─────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

.stApp, .main, [data-testid="stAppViewContainer"] {
    background: #000000 !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Sidebar ──────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #0a0a0a !important;
    border-right: 1px solid #1a1a1a !important;
}

/* ── Nav links — identical across ALL pages ────────────────────── */
[data-testid="stSidebarNav"] a {
    color: #a1a1aa !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    letter-spacing: 0.01em !important;
    padding: 8px 12px !important;
    border-radius: 6px !important;
    transition: all 0.15s ease !important;
    display: block !important;
}
[data-testid="stSidebarNav"] a:hover {
    color: #ffffff !important;
    background: #111111 !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebarNav"] a[aria-selected="true"] {
    color: #22c55e !important;
    background: rgba(34,197,94,0.08) !important;
    border-left: 2px solid #22c55e !important;
    padding-left: 10px !important;
}
[data-testid="stSidebarNav"] span {
    font-size: 14px !important;
    font-weight: 500 !important;
}

/* ── Headings ─────────────────────────────────────────────────── */
h1 {
    font-family: 'Inter', sans-serif !important;
    font-size: 26px !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    letter-spacing: -0.02em !important;
}
h2 {
    font-family: 'Inter', sans-serif !important;
    font-size: 18px !important;
    font-weight: 600 !important;
    color: #ffffff !important;
    letter-spacing: -0.01em !important;
    border-bottom: 1px solid #1a1a1a !important;
    padding-bottom: 10px !important;
    margin-bottom: 16px !important;
}
h3, h4 {
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
    border-color: #22c55e !important;
    background: rgba(34,197,94,0.04) !important;
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
[data-testid="stMetricDelta"][data-direction="up"]   { color: #22c55e !important; }
[data-testid="stMetricDelta"][data-direction="down"]  { color: #ef4444 !important; }

/* ── Buttons ──────────────────────────────────────────────────── */
.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    background: #22c55e !important;
    color: #000000 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 20px !important;
    transition: background 0.2s ease, transform 0.1s ease,
                box-shadow 0.2s ease !important;
    box-shadow: 0 0 0 0 rgba(34,197,94,0) !important;
}
.stButton > button:hover {
    background: #16a34a !important;
    box-shadow: 0 0 16px rgba(34,197,94,0.3) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
    background: #15803d !important;
}

/* Secondary button — outline style */
.stButton > button[kind="secondary"] {
    background: transparent !important;
    color: #22c55e !important;
    border: 1px solid #22c55e !important;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(34,197,94,0.08) !important;
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
    border-color: #22c55e !important;
    box-shadow: 0 0 0 3px rgba(34,197,94,0.1) !important;
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
    border-color: #22c55e !important;
}
[data-testid="stExpander"] summary {
    color: #ffffff !important;
    font-weight: 500 !important;
}

/* ── Dividers ─────────────────────────────────────────────────── */
hr {
    border: none !important;
    border-top: 1px solid #1a1a1a !important;
    margin: 20px 0 !important;
}

/* ── Scrollbar ────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #000000; }
::-webkit-scrollbar-thumb {
    background: #22c55e;
    border-radius: 2px;
}
::-webkit-scrollbar-thumb:hover { background: #16a34a; }

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
}
[data-testid="stTabs"] [role="tab"]:hover {
    color: #ffffff !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: #22c55e !important;
    border-bottom: 2px solid #22c55e !important;
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

    st.markdown("<h2 style='color:#22c55e;border-bottom:1px solid #1a1a1a;padding-bottom:8px;font-family:Inter,sans-serif'>Sign In</h2>", unsafe_allow_html=True)
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
    st.markdown(f"**{display_name}**")
    st.caption(st.session_state.get("email", ""))
    st.divider()
    st.page_link("pages/01_daily_brief.py",   label="Daily Brief")
    st.page_link("pages/02_stock_research.py", label="Stock Research")
    st.page_link("pages/03_portfolio.py",      label="Portfolio")
    st.page_link("pages/04_watchlist.py",      label="Watchlist")
    st.divider()
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
    st.page_link("pages/01_daily_brief.py", label="Open Daily Brief")

with col2:
    st.markdown("### Stock Research")
    st.write("Enter any ticker for a five-agent deep dive: news, SEC filings, financials, and a Buy/Hold/Sell verdict.")
    st.page_link("pages/02_stock_research.py", label="Open Research")
