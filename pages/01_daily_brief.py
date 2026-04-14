"""
Page 1 — Daily Brief
Portfolio overview, movers, unified news summary, macro alerts, signals, sources.
"""
import asyncio

import streamlit as st

from brief import generate_daily_brief
from data.firestore_client import get_todays_brief

st.set_page_config(page_title="Daily Brief | MarketMind", layout="wide")

# ── Badge helpers ─────────────────────────────────────────────────────────────

SIGNAL_STYLE = {
    "BUY":  "background:#1a2800;color:#76b900;border:1px solid #76b900",
    "SELL": "background:#2d0000;color:#ef4444;border:1px solid #ef4444",
    "WAIT": "background:#1a1a00;color:#facc15;border:1px solid #facc15",
}
SENTIMENT_STYLE = {
    "bullish": "background:#1a0533;color:#a78bfa;border:1px solid #7c3aed",
    "bearish": "background:#2d0000;color:#ef4444;border:1px solid #ef4444",
    "mixed":   "background:#1a1a00;color:#facc15;border:1px solid #facc15",
    "neutral": "background:#1a1a1a;color:#9ca3af;border:1px solid #374151",
}

def signal_badge(signal: str) -> str:
    style = SIGNAL_STYLE.get(signal.upper(), SIGNAL_STYLE["WAIT"])
    return (f"<span style='padding:3px 14px;border-radius:20px;"
            f"font-weight:600;font-size:13px;{style}'>{signal.upper()}</span>")

def section_header(title: str) -> None:
    st.markdown(
        f"<h2 style='color:#7c3aed;border-bottom:1px solid #1a1a1a;"
        f"padding-bottom:8px'>{title}</h2>",
        unsafe_allow_html=True,
    )

# ── Auth gate ─────────────────────────────────────────────────────────────────

uid = st.session_state.get("uid")
if not uid:
    st.warning("Please log in from the home page.")
    st.stop()

st.title("Daily Brief")

# ── Load / Generate ───────────────────────────────────────────────────────────

brief = get_todays_brief(uid)

col_refresh, _ = st.columns([1, 5])
with col_refresh:
    if st.button("Generate Today's Brief", type="primary"):
        brief = None  # force regeneration

if brief is None:
    with st.status("Generating your daily brief...", expanded=True) as status:
        st.write("Fetching latest news and computing portfolio...")
        brief = asyncio.run(generate_daily_brief(uid))
        st.write("Brief complete.")
        status.update(label="Daily brief ready!", state="complete")

if brief.get("empty"):
    st.info(brief["message"])
    st.stop()

snapshot = brief.get("portfolio_snapshot", {})
holdings = snapshot.get("holdings", [])
total_market  = snapshot.get("total_market_value", 0)
total_pnl     = snapshot.get("total_pnl", 0)
total_pnl_pct = snapshot.get("total_pnl_pct", 0)

# Approximate portfolio daily P&L from per-holding data
daily_pnl     = sum(h.get("market_value", 0) * h.get("daily_pct", 0) / 100 for h in holdings)
daily_pnl_pct = daily_pnl / total_market * 100 if total_market else 0.0

# ── Section 1 — Portfolio Overview ───────────────────────────────────────────

section_header("Portfolio Overview")
col1, col2, col3 = st.columns(3)
col1.metric("Total Value",  f"${total_market:,.2f}")
col2.metric("Today",        f"${daily_pnl:+,.2f}",  f"{daily_pnl_pct:+.2f}%")
col3.metric("Total P&L",    f"${total_pnl:+,.2f}",  f"{total_pnl_pct:+.2f}%")

# ── Section 2 — Today's Movers ────────────────────────────────────────────────

if holdings:
    section_header("Today's Movers")
    sorted_holdings = sorted(holdings, key=lambda x: abs(x.get("daily_pct", 0)), reverse=True)
    cols = st.columns(min(len(sorted_holdings), 5))
    for i, h in enumerate(sorted_holdings):
        cols[i % 5].metric(
            label=h["ticker"],
            value=f"${h['current_price']:.2f}",
            delta=f"{h['daily_pct']:+.2f}%",
        )

st.markdown("---")

# ── Section 3 — Portfolio News Summary ───────────────────────────────────────

section_header("Portfolio Summary")
summary_data = brief.get("portfolio_summary", {})
summary_text = summary_data.get("summary", "Summary unavailable.")
label        = summary_data.get("sentiment_label", "neutral")
score        = float(summary_data.get("sentiment_score", 5.0))

st.markdown(
    f"<p style='font-size:16px;line-height:1.9;color:#e0e0e0;"
    f"background:#0f0f0f;padding:20px;border-radius:10px;"
    f"border-left:3px solid #7c3aed'>{summary_text}</p>",
    unsafe_allow_html=True,
)
style = SENTIMENT_STYLE.get(label, SENTIMENT_STYLE["neutral"])
st.markdown(
    f"<span style='padding:4px 14px;border-radius:20px;"
    f"font-size:13px;font-weight:600;{style}'>{label.capitalize()}</span>"
    f"<span style='color:#6b7280;font-size:13px;margin-left:10px'>"
    f"Sentiment {score:.1f}/10</span>",
    unsafe_allow_html=True,
)

st.markdown("---")

# ── Section 4 — Global Headlines ─────────────────────────────────────────────

section_header("Global Headlines to Watch")
macro = brief.get("macro_alerts", [])
if not macro:
    st.caption("No significant macro events detected for your portfolio today.")
else:
    IMPACT_STYLE = {
        "bullish": "color:#a78bfa",
        "bearish": "color:#ef4444",
        "neutral": "color:#9ca3af",
    }
    for m in macro:
        impact   = m.get("impact", "neutral")
        color    = IMPACT_STYLE.get(impact, "color:#9ca3af")
        score_m  = m.get("relevance_score", 0)
        url      = m.get("url") or ""
        headline = m.get("headline", "")
        headline_html = (
            f"<a href='{url}' style='color:#e0e0e0;text-decoration:none'>{headline}</a>"
            if url else headline
        )
        st.markdown(
            f"<div style='background:#0f0f0f;border-radius:8px;"
            f"padding:12px 16px;margin-bottom:8px;"
            f"border-left:3px solid #7c3aed'>"
            f"<span style='font-size:14px;font-weight:600;color:#e0e0e0'>"
            f"{headline_html}</span><br>"
            f"<span style='font-size:13px;{color}'>{m.get('why_matters','')}</span>"
            f"<span style='float:right;font-size:11px;color:#6b7280'>"
            f"Relevance {score_m}/10</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

st.markdown("---")

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
else:
    st.caption("No signals generated.")

st.markdown("---")

# ── Section 5 — Source Links ─────────────────────────────────────────────────

section_header("Further Reading")
sources = brief.get("sources", [])
if not sources:
    st.caption("No source links available.")
else:
    for s in sources:
        ticker   = s.get("ticker", "")
        headline = s.get("headline", "")[:80]
        url      = s.get("url", "")
        domain   = s.get("domain", "")
        pub      = s.get("published_at", "")
        st.markdown(
            f"<div style='margin-bottom:6px'>"
            f"<span style='font-size:11px;color:#7c3aed;font-weight:600'>{ticker}</span> "
            f"<a href='{url}' style='color:#e0e0e0;font-size:13px'>{headline}...</a> "
            f"<span style='color:#6b7280;font-size:11px'>· {domain} · {pub}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

generated_at = brief.get("generated_at", "")
if generated_at:
    st.caption(f"Generated at {generated_at} UTC")
