"""
Page 1 — Daily Brief
Shows today's portfolio P&L, per-stock news, macro alerts, and buy/wait signals.
"""
import asyncio

import streamlit as st

from brief import generate_daily_brief
from data.firestore_client import get_todays_brief

st.set_page_config(page_title="Daily Brief | MarketMind", layout="wide")

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
st.markdown("<h2 style='color:#00d4ff'>Portfolio Performance</h2>", unsafe_allow_html=True)
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
st.markdown("<h2 style='color:#7ee8a2'>News Brief</h2>", unsafe_allow_html=True)
stock_news = brief.get("stock_news", {})
for ticker, news in stock_news.items():
    sentiment = news.get("sentiment", "neutral")
    SENTIMENT_COLORS = {
        "bullish": "background:#065f46;color:#6ee7b7",
        "bearish": "background:#7f1d1d;color:#fca5a5",
        "neutral": "background:#1f2937;color:#9ca3af",
    }
    sentiment_style = SENTIMENT_COLORS.get(sentiment, SENTIMENT_COLORS["neutral"])
    sentiment_label = {"bullish": "Bullish", "bearish": "Bearish", "neutral": "Neutral"}.get(sentiment, "Neutral")
    st.markdown(f"**{ticker}** — {news.get('top_headline', 'No headline')}")
    st.markdown(
        f"<span style='padding:4px 12px;border-radius:20px;font-weight:600;{sentiment_style}'>"
        f"{sentiment_label}</span>",
        unsafe_allow_html=True,
    )
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
    st.markdown("<h2 style='color:#f59e0b'>Macro Alerts</h2>", unsafe_allow_html=True)
    for alert in macro:
        score     = alert.get("relevance_score", 0)
        direction = alert.get("impact_direction", "neutral")
        arrow     = {"positive": "↑", "negative": "↓", "neutral": "→"}.get(direction, "→")
        st.markdown(
            f"**[{score}/10]** {arrow} {alert.get('headline', '')}  \n"
            f"*{alert.get('source', '')}* — {alert.get('why_matters', '')}"
        )

# ── Buy / Wait / Sell Signals ─────────────────────────────────────────────────
st.markdown("<h2 style='color:#a78bfa'>Signals</h2>", unsafe_allow_html=True)
signals = brief.get("signals", {})
SIGNAL_COLORS = {
    "BUY":  "background:#065f46;color:#6ee7b7",
    "SELL": "background:#7f1d1d;color:#fca5a5",
    "WAIT": "background:#1e3a5f;color:#93c5fd",
}
if signals:
    for ticker, sig in signals.items():
        signal_val = sig.get("signal", "WAIT")
        urgency    = sig.get("urgency", "LOW")
        style      = SIGNAL_COLORS.get(signal_val, SIGNAL_COLORS["WAIT"])
        st.markdown(
            f"<span style='padding:4px 12px;border-radius:20px;font-weight:600;{style}'>"
            f"{signal_val}</span>"
            f" &nbsp; **{ticker}** &nbsp; `{urgency}` &nbsp; — {sig.get('reason', '')}",
            unsafe_allow_html=True,
        )
        if sig.get("watch_price"):
            st.caption(f"Watch price: ${sig['watch_price']:.2f}")

generated_at = brief.get("generated_at", "")
if generated_at:
    st.caption(f"Generated at {generated_at} UTC")
