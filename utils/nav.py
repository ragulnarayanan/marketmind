"""
Shared sidebar navigation — import and call render_nav() in every page.
Uses st.page_link() so Streamlit preserves session state across pages.
"""
import streamlit as st


_NAV_CSS = """
<style>
/* ── Hide Streamlit auto-nav ─────────────────────────────────────── */
[data-testid="stSidebarNav"],
[data-testid="stSidebarNav"] * {
    display: none !important;
    visibility: hidden !important;
    pointer-events: none !important;
}

/* ── Buttons — solid green, black text ──────────────────────────── */
.stButton > button,
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-secondary"],
button[data-testid="stBaseButton-tertiary"],
[data-testid="stForm"] button,
.stButton button {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    background: #76b900 !important;
    color: #000000 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 24px !important;
    transition: background 0.2s ease, transform 0.1s ease,
                box-shadow 0.2s ease !important;
    text-transform: none !important;
}
.stButton > button *,
button[data-testid="stBaseButton-primary"] *,
button[data-testid="stBaseButton-secondary"] *,
button[data-testid="stBaseButton-tertiary"] *,
.stButton button * {
    color: #000000 !important;
}
.stButton > button:hover,
button[data-testid="stBaseButton-primary"]:hover,
button[data-testid="stBaseButton-secondary"]:hover,
button[data-testid="stBaseButton-tertiary"]:hover {
    background: #8fd400 !important;
    box-shadow: 0 0 16px rgba(118,185,0,0.3) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active,
button[data-testid="stBaseButton-primary"]:active,
button[data-testid="stBaseButton-secondary"]:active {
    transform: translateY(0) !important;
    background: #5a8c00 !important;
}
</style>
"""


def render_nav() -> None:
    """Render the MarketMind sidebar nav. Call this at the top of every page."""
    st.markdown(_NAV_CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown(
            "<div style='padding:20px 12px 8px'>"
            "<span style='color:#ffffff;font-size:20px;font-weight:700;"
            "font-family:Inter,sans-serif;letter-spacing:-0.02em'>"
            "MarketM<span style='position:relative;display:inline-block'>&#x131;"
            "<span style='position:absolute;left:50%;top:0.24em;transform:translateX(-50%);"
            "width:0.2em;height:0.2em;background:#76b900;border-radius:50%;display:block'>"
            "</span></span>nd</span></div>",
            unsafe_allow_html=True,
        )

        st.page_link("app.py",                      label="Home")
        st.page_link("pages/01_daily_brief.py",     label="Daily Brief")
        st.page_link("pages/02_stock_research.py",  label="Stock Research")
        st.page_link("pages/03_portfolio.py",        label="Portfolio")

        st.markdown(
            "<div style='height:1px;background:#1a1a1a;margin:14px 8px'></div>",
            unsafe_allow_html=True,
        )

        display_name = st.session_state.get("display_name", "")
        email        = st.session_state.get("email", "")
        if display_name:
            st.markdown(
                f"<div style='padding:4px 12px 8px'>"
                f"<span style='color:#ffffff;font-size:13px;font-weight:500;"
                f"font-family:Inter,sans-serif'>{display_name}</span><br>"
                f"<span style='color:#52525b;font-size:12px;"
                f"font-family:Inter,sans-serif'>{email}</span></div>",
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button("Sign Out", key="nav_sign_out"):
                for key in ["uid", "display_name", "email"]:
                    st.session_state.pop(key, None)
                st.switch_page("app.py")
