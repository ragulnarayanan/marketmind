"""
Page 2 — Stock Research
Five-agent deep dive on any ticker → Buy / Hold / Sell verdict.
"""
import asyncio

import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from agents import run_stock_research

st.set_page_config(page_title="Stock Research | MarketMind", layout="wide")

uid = st.session_state.get("uid")
if not uid:
    st.warning("Please log in from the home page.")
    st.stop()

st.title("Stock Research")

# ── Input ─────────────────────────────────────────────────────────────────────
col_input, col_btn = st.columns([3, 1])
with col_input:
    ticker_input = st.text_input("Ticker", placeholder="AAPL", key="research_ticker_input").upper().strip()
with col_btn:
    st.write("")
    research_btn = st.button("Research", type="primary", use_container_width=True)

# ── Validate + fetch ──────────────────────────────────────────────────────────
if research_btn and ticker_input:
    cache_key = f"research_{ticker_input}"
    st.session_state[cache_key] = None  # clear stale cache

    try:
        yf.Ticker(ticker_input).fast_info["lastPrice"]
    except Exception:
        st.error(f"'{ticker_input}' does not appear to be a valid ticker.")
        st.stop()

    with st.status(f"Researching {ticker_input}...", expanded=True) as status:
        st.write("Fetching news and SEC filings...")
        st.write("Running News Agent (gpt-4o-mini)...")
        st.write("Running SEC Agent (gemini-1.5-pro)...")
        st.write("Running Financials Agent (gemini-1.5-flash)...")
        st.write("Running Synthesis Agent (gpt-4o-mini)...")
        st.write("Running Verdict Agent (gpt-4o)...")
        result = asyncio.run(run_stock_research(ticker_input))
        st.session_state[cache_key] = result
        status.update(label="Research complete!", state="complete")

# ── Display ───────────────────────────────────────────────────────────────────
cache_key = f"research_{ticker_input}" if ticker_input else None
result = st.session_state.get(cache_key) if cache_key else None

if result is None:
    st.info("Enter a ticker and click Research to begin.")
    st.stop()

# Price + volume chart
try:
    hist = yf.Ticker(ticker_input).history(period="1y")
    if not hist.empty:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=hist.index, open=hist["Open"], high=hist["High"],
            low=hist["Low"], close=hist["Close"], name="Price",
        ))
        fig.add_trace(go.Bar(
            x=hist.index, y=hist["Volume"], name="Volume",
            marker_color="rgba(124,58,237,0.3)", yaxis="y2",
        ))
        fig.update_layout(
            title=f"{ticker_input} — 1-Year Price and Volume",
            yaxis2=dict(overlaying="y", side="right", showgrid=False),
            xaxis_rangeslider_visible=False,
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)
except Exception:
    pass

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_news, tab_sec, tab_fin, tab_verdict = st.tabs(["News", "SEC Filing", "Financials", "Verdict"])

with tab_news:
    news = result.get("news", {})
    sentiment = news.get("sentiment_label", "neutral")
    sentiment_color = {"bullish": "green", "bearish": "red", "neutral": "orange"}.get(sentiment, "orange")
    sentiment_label = {"bullish": "BULLISH", "bearish": "BEARISH", "neutral": "NEUTRAL"}.get(sentiment, sentiment.upper())
    st.markdown(f"### :{sentiment_color}[{sentiment_label}]  — Score {news.get('sentiment_score', 'N/A')}/10")
    st.write(news.get("summary", ""))
    st.caption(f"Top headline: {news.get('top_headline', 'N/A')}")

    col_ev, col_risk = st.columns(2)
    with col_ev:
        st.markdown("**Key Events**")
        for ev in news.get("key_events", []):
            st.markdown(f"- {ev}")
    with col_risk:
        st.markdown("**Risks**")
        for r in news.get("risks", []):
            st.markdown(f"- {r}")

with tab_sec:
    sec = result.get("sec", {})
    filing_type = sec.get("filing_type", "10-K")
    st.markdown(f"#### {filing_type} Filing Analysis")
    sections = [
        ("Risk Factors",         "risk_factors"),
        ("Revenue and Outlook",  "revenue_outlook"),
        ("Debt and Going Concern","debt_concerns"),
        ("Competitive Threats",  "competitive_threats"),
        ("Capital Allocation",   "capital_allocation"),
    ]
    for label, key in sections:
        item = sec.get(key, {})
        conf = item.get("confidence", "low")
        conf_label = {"high": "[High]", "medium": "[Med]", "low": "[Low]"}.get(conf, "[?]")
        with st.expander(f"{conf_label} {label}"):
            st.write(item.get("answer", "N/A"))

with tab_fin:
    fin = result.get("financials", {})
    if fin.get("error"):
        st.error(f"Financials unavailable: {fin['error']}")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Valuation",       fin.get("valuation", "N/A"))
        c2.metric("Financial Health", fin.get("financial_health", "N/A"))
        c3.metric("Growth Profile",  fin.get("growth_profile", "N/A"))

        st.markdown("**Valuation Rationale:** " + fin.get("valuation_reason", "N/A"))
        st.markdown("**Health Rationale:** " + fin.get("health_reason", "N/A"))

        metrics = fin.get("key_metrics", {})
        if metrics:
            st.markdown("#### Key Metrics")
            m_cols = st.columns(4)
            pairs = [("P/E", "pe"), ("P/B", "pb"), ("EV/EBITDA", "ev_ebitda"),
                     ("Margin", "margin"), ("D/E", "de_ratio"), ("ROE", "roe"), ("Beta", "beta")]
            for i, (lbl, key) in enumerate(pairs):
                v = metrics.get(key)
                m_cols[i % 4].metric(lbl, f"{v:.2f}" if v is not None else "N/A")

        col_flags1, col_flags2 = st.columns(2)
        with col_flags1:
            st.markdown("**Red Flags**")
            for f in fin.get("red_flags", []):
                st.markdown(f"- {f}")
        with col_flags2:
            st.markdown("**Green Flags**")
            for f in fin.get("green_flags", []):
                st.markdown(f"- {f}")

with tab_verdict:
    verdict = result.get("verdict", {})
    v     = verdict.get("verdict", "HOLD")
    conf  = verdict.get("confidence", "LOW")
    score = verdict.get("confidence_score", 0)

    verdict_color = {"BUY": "green", "SELL": "red", "HOLD": "orange"}.get(v, "orange")
    st.markdown(f"## :{verdict_color}[{v}]  — Confidence: {conf}  ({score}/10)")
    st.progress(score * 10, text=f"Confidence score: {score}/10")

    st.markdown("**Reasoning**")
    for point in verdict.get("reasoning", []):
        st.markdown(f"- {point}")

    col_bull, col_bear = st.columns(2)
    with col_bull:
        st.markdown("**Bull Case**")
        st.write(verdict.get("bull_case", "N/A"))
    with col_bear:
        st.markdown("**Bear Case**")
        st.write(verdict.get("bear_case", "N/A"))

    st.markdown("**Key Risks**")
    for risk in verdict.get("key_risks", []):
        st.markdown(f"- {risk}")

    horizon = verdict.get("time_horizon", "MEDIUM")
    st.markdown(f"**Time Horizon:** {horizon}")
    if verdict.get("price_context"):
        st.markdown(f"**Price Context:** {verdict['price_context']}")

    st.caption(verdict.get("disclaimer", "Not financial advice. Do your own research."))
