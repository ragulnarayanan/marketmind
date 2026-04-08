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

# Hide Streamlit's auto-generated page navigation (we use custom links below)
st.markdown(
    "<style>[data-testid='stSidebarNav']{display:none!important}</style>",
    unsafe_allow_html=True,
)

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

    st.subheader("Sign In")
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
