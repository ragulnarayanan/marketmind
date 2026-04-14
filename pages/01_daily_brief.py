"""
Page 1 — Daily Brief
Shows today's portfolio P&L, per-stock news, macro alerts, and buy/wait signals.
"""
import asyncio

import streamlit as st

from brief import generate_daily_brief
from data.firestore_client import get_todays_brief

st.set_page_config(page_title="Daily Brief | MarketMind", layout="wide")

SIGNAL_STYLE = {
    "BUY":  "background:#1a2800;color:#76b900;border:1px solid #76b900",
    "SELL": "background:#2d0000;color:#ef4444;border:1px solid #ef4444",
    "WAIT": "background:#1a1a00;color:#facc15;border:1px solid #facc15",
}
SENTIMENT_STYLE = {
    "bullish": "background:#1a2800;color:#76b900;border:1px solid #76b900",
    "bearish": "background:#2d0000;color:#ef4444;border:1px solid #ef4444",
    "neutral": "background:#1a1a1a;color:#9ca3af;border:1px solid #374151",
}

def signal_badge(signal: str) -> str:
    style = SIGNAL_STYLE.get(signal.upper(), SIGNAL_STYLE["WAIT"])
    return (f"<span style='padding:3px 14px;border-radius:20px;"
            f"font-weight:600;font-size:13px;{style}'>{signal.upper()}</span>")

def sentiment_badge(label: str) -> str:
    style = SENTIMENT_STYLE.get(label.lower(), SENTIMENT_STYLE["neutral"])
    return (f"<span style='padding:3px 12px;border-radius:20px;"
            f"font-size:12px;{style}'>{label.capitalize()}</span>")

def section_header(title: str) -> None:
    st.markdown(
        f"<h2 style='color:#76b900;border-bottom:1px solid #1a1a1a;"
        f"padding-bottom:8px'>{title}</h2>",
        unsafe_allow_html=True,
    )

uid = st.session_state.get("uid")
if not uid:
    st.warning("Please log in from the home page.")
    st.stop()

st.title("Daily Brief")

# ── Load / Generate ───────────────────────────────────────────────────────────
brief = get_todays_brief(uid)

col_refresh, col_info = st.columns([1, 5])
with col_refresh:
    if st.button("Generate Today's Brief", type="primary"):
        brief = None  # force regeneration

if brief is None:
    with st.status("Generating your daily brief...", expanded=True) as status:
        st.write("Fetching latest news...")
        brief = asyncio.run(generate_daily_brief(uid))
        st.write("Brief complete.")
        status.update(label="Daily brief ready!", state="complete")

if brief.get("empty"):
    st.info(brief["message"])
    st.stop()

# ── Portfolio Performance ─────────────────────────────────────────────────────
section_header("Portfolio Performance")
snapshot = brief.get("portfolio_snapshot", {})
holdings = snapshot.get("holdings", [])

if holdings:
    cols = st.columns(min(len(holdings), 4))
    for i, h in enumerate(holdings):
        col = cols[i % len(cols)]
        col.metric(
            label=h["ticker"],
            value=f"${h['market_value']:,.2f}",
            delta=f"{h['daily_pct']:+.2f}% today",
        )

    total_pnl     = snapshot.get("total_pnl", 0)
    total_pnl_pct = snapshot.get("total_pnl_pct", 0)
    total_market  = snapshot.get("total_market_value", 0)

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Portfolio Value", f"${total_market:,.2f}")
    c2.metric("Total P&L",             f"${total_pnl:+,.2f}", delta=f"{total_pnl_pct:+.2f}%")
    c3.metric("Positions",             str(len(holdings)))

# ── Per-Stock News ────────────────────────────────────────────────────────────
section_header("News Brief")
stock_news = brief.get("stock_news", {})
for ticker, news in stock_news.items():
    sentiment = news.get("sentiment", "neutral")
    st.markdown(f"**{ticker}** — {news.get('top_headline', 'No headline')}")
    st.markdown(sentiment_badge(sentiment), unsafe_allow_html=True)
    summary_text = news.get("summary", "")
    st.markdown(
        f"<p style='font-size:15px; line-height:1.7;'>{summary_text}</p>",
        unsafe_allow_html=True,
    )
    score = news.get("score", 5.0)
    st.progress(min(int(score * 10), 100), text=f"Sentiment score: {score:.1f}/10")
    sources = news.get("sources", [])
    if sources:
        st.markdown("**Sources:**")
        for s in sources:
            url         = s.get("url", "")
            headline    = s.get("headline", "")
            source_name = s.get("source_name", "")
            domain      = s.get("domain", source_name)
            published   = s.get("published_at", "")
            if url and headline:
                st.markdown(
                    f"→ [{headline[:70]}...]({url})  "
                    f"<span style='color:gray;font-size:12px'>{domain} · {published}</span>",
                    unsafe_allow_html=True,
                )
    else:
        st.caption("No source links available for this ticker.")
    st.markdown("---")

# ── Macro Alerts ──────────────────────────────────────────────────────────────
macro = brief.get("macro_alerts", [])
if macro:
    section_header("Macro Alerts")
    for alert in macro:
        score     = alert.get("relevance_score", 0)
        direction = alert.get("impact_direction", "neutral")
        arrow     = {"positive": "↑", "negative": "↓", "neutral": "→"}.get(direction, "→")
        st.markdown(
            f"**[{score}/10]** {arrow} {alert.get('headline', '')}  \n"
            f"*{alert.get('source', '')}* — {alert.get('why_matters', '')}"
        )

# ── Buy / Wait / Sell Signals ─────────────────────────────────────────────────
section_header("Signals")
signals = brief.get("signals", {})
if signals:
    for ticker, sig in signals.items():
        signal_val = sig.get("signal", "WAIT")
        urgency    = sig.get("urgency", "LOW")
        st.markdown(
            f"{signal_badge(signal_val)}"
            f" &nbsp; **{ticker}** &nbsp; `{urgency}` &nbsp; — {sig.get('reason', '')}",
            unsafe_allow_html=True,
        )
        if sig.get("watch_price"):
            st.caption(f"Watch price: ${sig['watch_price']:.2f}")

generated_at = brief.get("generated_at", "")
if generated_at:
    st.caption(f"Generated at {generated_at} UTC")
