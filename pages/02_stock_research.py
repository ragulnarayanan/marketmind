"""
Page 2 — Stock Research
Five-agent deep dive on up to 5 tickers → Buy / Hold / Sell verdict.
"""
import asyncio
import os

import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from agents import run_stock_research
from utils.nav import render_nav
from utils.ui_components import green_badge, neutral_badge, red_badge, sentiment_badge, signal_badge

st.set_page_config(page_title="Stock Research | MarketMind", layout="wide")

uid = st.session_state.get("uid")
if not uid:
    st.switch_page("app.py")
    st.stop()

render_nav()

st.title("Stock Research")

TOP_50 = [
    {"symbol": "AAPL",  "name": "Apple Inc."},
    {"symbol": "MSFT",  "name": "Microsoft Corp."},
    {"symbol": "NVDA",  "name": "NVIDIA Corp."},
    {"symbol": "GOOGL", "name": "Alphabet Inc."},
    {"symbol": "AMZN",  "name": "Amazon.com"},
    {"symbol": "META",  "name": "Meta Platforms"},
    {"symbol": "TSLA",  "name": "Tesla Inc."},
    {"symbol": "AVGO",  "name": "Broadcom Inc."},
    {"symbol": "TSM",   "name": "Taiwan Semiconductor"},
    {"symbol": "LLY",   "name": "Eli Lilly"},
    {"symbol": "V",     "name": "Visa Inc."},
    {"symbol": "JPM",   "name": "JPMorgan Chase"},
    {"symbol": "WMT",   "name": "Walmart Inc."},
    {"symbol": "MA",    "name": "Mastercard"},
    {"symbol": "XOM",   "name": "Exxon Mobil"},
    {"symbol": "COST",  "name": "Costco Wholesale"},
    {"symbol": "HD",    "name": "Home Depot"},
    {"symbol": "JNJ",   "name": "Johnson & Johnson"},
    {"symbol": "NFLX",  "name": "Netflix Inc."},
    {"symbol": "PG",    "name": "Procter & Gamble"},
    {"symbol": "ORCL",  "name": "Oracle Corp."},
    {"symbol": "BAC",   "name": "Bank of America"},
    {"symbol": "ABBV",  "name": "AbbVie Inc."},
    {"symbol": "AMD",   "name": "Advanced Micro Devices"},
    {"symbol": "CRM",   "name": "Salesforce"},
    {"symbol": "KO",    "name": "Coca-Cola Co."},
    {"symbol": "CVX",   "name": "Chevron Corp."},
    {"symbol": "MRK",   "name": "Merck & Co."},
    {"symbol": "PEP",   "name": "PepsiCo Inc."},
    {"symbol": "ADBE",  "name": "Adobe Inc."},
    {"symbol": "ACN",   "name": "Accenture PLC"},
    {"symbol": "WFC",   "name": "Wells Fargo"},
    {"symbol": "UNH",   "name": "UnitedHealth Group"},
    {"symbol": "IBM",   "name": "IBM Corp."},
    {"symbol": "QCOM",  "name": "Qualcomm Inc."},
    {"symbol": "NOW",   "name": "ServiceNow"},
    {"symbol": "TXN",   "name": "Texas Instruments"},
    {"symbol": "PM",    "name": "Philip Morris"},
    {"symbol": "INTU",  "name": "Intuit Inc."},
    {"symbol": "AMGN",  "name": "Amgen Inc."},
    {"symbol": "CSCO",  "name": "Cisco Systems"},
    {"symbol": "CAT",   "name": "Caterpillar Inc."},
    {"symbol": "DIS",   "name": "Walt Disney Co."},
    {"symbol": "GS",    "name": "Goldman Sachs"},
    {"symbol": "NEE",   "name": "NextEra Energy"},
    {"symbol": "ISRG",  "name": "Intuitive Surgical"},
    {"symbol": "BKNG",  "name": "Booking Holdings"},
    {"symbol": "AMAT",  "name": "Applied Materials"},
    {"symbol": "SPGI",  "name": "S&P Global"},
    {"symbol": "T",     "name": "AT&T Inc."},
]
SYMBOL_MAP = {s["symbol"]: s for s in TOP_50}

# ── Session state init ────────────────────────────────────────────────────────
if "research_queue" not in st.session_state:
    st.session_state["research_queue"] = []

# Auto-add ticker coming from Watchlist "Research" button
_redirect = st.session_state.pop("research_ticker_input", None)
if _redirect and _redirect in SYMBOL_MAP and _redirect not in st.session_state["research_queue"]:
    st.session_state["research_queue"].append(_redirect)

# ── Stock selector ────────────────────────────────────────────────────────────
sel_idx = st.selectbox(
    "Select stock",
    range(len(TOP_50)),
    format_func=lambda i: f"{TOP_50[i]['symbol']} — {TOP_50[i]['name']}",
    key="rs_stock_sel",
)
selected = TOP_50[sel_idx]

logo_col, name_col, btn_col = st.columns([1, 6, 1])
with logo_col:
    svg_path = f"assets/logos/{selected['symbol']}.svg"
    png_path = f"assets/logos/{selected['symbol']}.png"
    if os.path.exists(svg_path):
        raw = open(svg_path, "rb").read()
        if raw[:5] in (b"<?xml", b"<svg ") or b"<svg" in raw[:64]:
            st.markdown(f'<div style="width:48px;height:48px">{raw.decode("utf-8")}</div>', unsafe_allow_html=True)
        else:
            st.image(svg_path, width=48)
    elif os.path.exists(png_path):
        st.image(png_path, width=48)
with name_col:
    st.markdown(f"**{selected['name']}** &nbsp; `{selected['symbol']}`")
with btn_col:
    if st.button("+ Add", type="primary", use_container_width=True):
        ticker = selected["symbol"]
        if ticker in st.session_state["research_queue"]:
            st.warning(f"{ticker} is already in the queue.")
        elif len(st.session_state["research_queue"]) >= 5:
            st.warning("Queue is full — maximum 5 stocks.")
        else:
            st.session_state["research_queue"].append(ticker)
            st.rerun()

# ── Research queue ────────────────────────────────────────────────────────────
queue = st.session_state["research_queue"]

if queue:
    st.markdown("**Research Queue** (up to 5)")
    tag_cols = st.columns(len(queue) + 1)
    for i, ticker in enumerate(list(queue)):
        if tag_cols[i].button(f"{ticker}  x", key=f"rm_{ticker}"):
            st.session_state["research_queue"].remove(ticker)
            st.rerun()

    if tag_cols[-1].button("Research All", type="primary"):
        for ticker in queue:
            cache_key = f"rs_result_{ticker}"
            if st.session_state.get(cache_key):
                continue  # already cached
            with st.status(f"Researching {ticker}...", expanded=True) as status:
                st.write("Fetching news and SEC filings...")
                st.write("Running News, SEC, Financials, Synthesis, Verdict agents...")
                result = asyncio.run(run_stock_research(ticker))
                st.session_state[cache_key] = result
                status.update(label=f"{ticker} complete!", state="complete")
        st.rerun()
else:
    st.info("Select a stock above and click + Add to build your research queue.")
    st.stop()

# ── Results ───────────────────────────────────────────────────────────────────
ready = [(t, st.session_state.get(f"rs_result_{t}")) for t in queue if st.session_state.get(f"rs_result_{t}")]
if not ready:
    st.stop()

stock_tabs = st.tabs([t for t, _ in ready])

for tab, (ticker, result) in zip(stock_tabs, ready):
    with tab:
        # Price + volume chart
        try:
            hist = yf.Ticker(ticker).history(period="1y")
            if not hist.empty:
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=hist.index, open=hist["Open"], high=hist["High"],
                    low=hist["Low"], close=hist["Close"], name="Price",
                ))
                fig.add_trace(go.Bar(
                    x=hist.index, y=hist["Volume"], name="Volume",
                    marker_color="rgba(34,197,94,0.3)", yaxis="y2",
                ))
                fig.update_layout(
                    title=f"{ticker} — 1-Year Price and Volume",
                    yaxis2=dict(overlaying="y", side="right", showgrid=False),
                    xaxis_rangeslider_visible=False,
                    height=380,
                    template="plotly_dark",
                    paper_bgcolor="#000000",
                    plot_bgcolor="#0a0a0a",
                    font=dict(family="Inter, sans-serif", color="#a1a1aa"),
                )
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

        tab_news, tab_sec, tab_fin, tab_verdict = st.tabs(
            ["News", "SEC Filing", "Financials", "Verdict"]
        )

        with tab_news:
            news = result.get("news", {})
            sentiment = news.get("sentiment_label", "neutral")
            st.markdown(
                sentiment_badge(sentiment) +
                f"<span style='color:#52525b;font-size:13px;margin-left:10px;"
                f"font-family:Inter,sans-serif'>Score {news.get('sentiment_score', 'N/A')}/10</span>",
                unsafe_allow_html=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)
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
            st.markdown(f"#### {sec.get('filing_type', '10-K')} Filing Analysis")
            for label, key in [
                ("Risk Factors",          "risk_factors"),
                ("Revenue and Outlook",   "revenue_outlook"),
                ("Debt and Going Concern","debt_concerns"),
                ("Competitive Threats",   "competitive_threats"),
                ("Capital Allocation",    "capital_allocation"),
            ]:
                item = sec.get(key, {})
                conf_label = {"high": "[High]", "medium": "[Med]", "low": "[Low]"}.get(
                    item.get("confidence", "low"), "[?]"
                )
                with st.expander(f"{conf_label} {label}"):
                    st.write(item.get("answer", "N/A"))

        with tab_fin:
            fin = result.get("financials", {})
            if fin.get("error"):
                st.error(f"Financials unavailable: {fin['error']}")
            else:
                def _fmt(val: str) -> str:
                    return val.replace("_", " ").title() if val else "N/A"

                c1, c2, c3 = st.columns(3)
                c1.metric("Valuation",        _fmt(fin.get("valuation", "N/A")))
                c2.metric("Financial Health",  _fmt(fin.get("financial_health", "N/A")))
                c3.metric("Growth Profile",    _fmt(fin.get("growth_profile", "N/A")))
                st.markdown("**Valuation Rationale:** " + fin.get("valuation_reason", "N/A"))
                st.markdown("**Health Rationale:** "    + fin.get("health_reason", "N/A"))
                metrics = fin.get("key_metrics", {})
                if metrics:
                    st.markdown("#### Key Metrics")
                    m_cols = st.columns(4)
                    for i, (lbl, k) in enumerate([
                        ("P/E","pe"),("P/B","pb"),("EV/EBITDA","ev_ebitda"),
                        ("Margin","margin"),("D/E","de_ratio"),("ROE","roe"),("Beta","beta"),
                    ]):
                        v = metrics.get(k)
                        m_cols[i % 4].metric(lbl, f"{v:.2f}" if v is not None else "N/A")
                col_r, col_g = st.columns(2)
                with col_r:
                    st.markdown("**Red Flags**")
                    for f in fin.get("red_flags", []):
                        st.markdown(f"- {f}")
                with col_g:
                    st.markdown("**Green Flags**")
                    for f in fin.get("green_flags", []):
                        st.markdown(f"- {f}")

        with tab_verdict:
            verdict = result.get("verdict", {})
            v      = verdict.get("verdict", "HOLD")
            conf   = verdict.get("confidence", "LOW")
            score  = verdict.get("confidence_score", 0)
            v_upper = v.upper()
            if v_upper == "BUY":
                v_badge = green_badge("BUY")
            elif v_upper == "SELL":
                v_badge = red_badge("SELL")
            else:
                v_badge = neutral_badge(v_upper)
            st.markdown(
                v_badge +
                f"<span style='color:#a1a1aa;font-size:14px;margin-left:12px;"
                f"font-family:Inter,sans-serif'>Confidence: {conf} &nbsp;·&nbsp; "
                f"{score}/10</span>",
                unsafe_allow_html=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)
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
            st.markdown(f"**Time Horizon:** {verdict.get('time_horizon', 'MEDIUM')}")
            if verdict.get("price_context"):
                st.markdown(f"**Price Context:** {verdict['price_context']}")
            st.caption(verdict.get("disclaimer", "Not financial advice. Do your own research."))
