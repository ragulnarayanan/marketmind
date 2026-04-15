"""
Shared sidebar navigation — import and call render_nav() in every page.
Uses st.page_link() so Streamlit preserves session state across pages.
"""
import streamlit as st


def render_nav() -> None:
    """Render the MarketMind sidebar nav. Call this at the top of every page."""
    with st.sidebar:
        st.markdown(
            "<div style='padding:20px 12px 8px'>"
            "<span style='color:#76b900;font-size:20px;font-weight:700;"
            "font-family:Inter,sans-serif;letter-spacing:-0.02em'>"
            "MarketMind</span></div>",
            unsafe_allow_html=True,
        )

        st.page_link("app.py",                      label="Home")
        st.page_link("pages/01_daily_brief.py",     label="Daily Brief")
        st.page_link("pages/02_stock_research.py",  label="Stock Research")
        st.page_link("pages/03_portfolio.py",        label="Portfolio")
        st.page_link("pages/04_watchlist.py",        label="Watchlist")

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
