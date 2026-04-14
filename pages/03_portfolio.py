"""
Page 3 — Portfolio Manager
Add / edit / delete holdings. Shows live price + P&L.
"""
import os

import streamlit as st
import yfinance as yf

from brief.portfolio_pnl import compute_portfolio_snapshot
from data.firestore_client import get_portfolio, remove_holding, upsert_holding

st.set_page_config(page_title="Portfolio | MarketMind", layout="wide")


@st.cache_data(ttl=60, show_spinner=False)
def _load_snapshot(holdings_key: tuple) -> dict:
    """Cache live prices for 60 s so dropdown changes don't re-fetch."""
    portfolio = [{"ticker": t, "qty": q, "avg_cost": c} for t, q, c in holdings_key]
    return compute_portfolio_snapshot(portfolio)


uid = st.session_state.get("uid")
if not uid:
    st.warning("Please log in from the home page.")
    st.stop()

st.title("Portfolio")

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

portfolio = get_portfolio(uid)

# ── Live P&L table ────────────────────────────────────────────────────────────
if portfolio:
    holdings_key = tuple((h["ticker"], h["qty"], h["avg_cost"]) for h in portfolio)
    with st.spinner("Loading live prices..."):
        snapshot = _load_snapshot(holdings_key)

    holdings_display = snapshot.get("holdings", [])
    if holdings_display:
        st.markdown("<h2 style='color:#76b900;border-bottom:1px solid #1a1a1a;padding-bottom:8px'>Holdings</h2>", unsafe_allow_html=True)
        header_cols = st.columns([2, 1, 1, 1, 1, 1, 1])
        for col, label in zip(
            header_cols,
            ["Ticker", "Shares", "Avg Cost", "Current", "Daily %", "P&L", "Action"],
        ):
            col.markdown(f"**{label}**")

        for row in holdings_display:
            cols = st.columns([2, 1, 1, 1, 1, 1, 1])
            cols[0].write(row["ticker"])
            cols[1].write(f"{row['qty']:.2f}")
            cols[2].write(f"${row['avg_cost']:.2f}")
            cols[3].write(f"${row['current_price']:.2f}")
            daily_color = "green" if row["daily_pct"] >= 0 else "red"
            cols[4].markdown(f":{daily_color}[{row['daily_pct']:+.2f}%]")
            pnl_color = "green" if row["total_pnl"] >= 0 else "red"
            cols[5].markdown(f":{pnl_color}[${row['total_pnl']:+,.2f} ({row['total_pnl_pct']:+.2f}%)]")
            if cols[6].button("Remove", key=f"del_{row['ticker']}"):
                remove_holding(uid, row["ticker"])
                st.rerun()

        st.markdown("---")
        total = snapshot
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Value", f"${total['total_market_value']:,.2f}")
        c2.metric("Total P&L",   f"${total['total_pnl']:+,.2f}",
                  delta=f"{total['total_pnl_pct']:+.2f}%")
        c3.metric("Positions",   str(len(holdings_display)))
else:
    st.info("Your portfolio is empty. Add your first holding below.")

# ── Add / Update Holding ──────────────────────────────────────────────────────
st.markdown("---")
st.markdown("<h2 style='color:#76b900;border-bottom:1px solid #1a1a1a;padding-bottom:8px'>Add / Update Holding</h2>", unsafe_allow_html=True)

sel_idx = st.selectbox(
    "Select stock",
    range(len(TOP_50)),
    format_func=lambda i: f"{TOP_50[i]['symbol']} — {TOP_50[i]['name']}",
    key="pf_stock_sel",
)
selected = TOP_50[sel_idx]

# Logo + name preview
logo_col, name_col = st.columns([1, 8])
with logo_col:
    logo_path = f"assets/logos/{selected['symbol']}.svg"
    if os.path.exists(logo_path):
        svg = open(logo_path).read()
        st.markdown(f'<div style="width:48px;height:48px">{svg}</div>', unsafe_allow_html=True)
with name_col:
    st.markdown(f"**{selected['name']}** &nbsp; `{selected['symbol']}`")

with st.form("add_holding_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        new_qty  = st.number_input("Shares", min_value=0.01, step=1.0, value=1.0)
    with col2:
        new_cost = st.number_input("Avg Cost ($)", min_value=0.01, step=0.01, value=100.0)
    submitted = st.form_submit_button("Add Holding", type="primary")

if submitted:
    ticker = TOP_50[st.session_state["pf_stock_sel"]]["symbol"]
    upsert_holding(uid, ticker, new_qty, new_cost)
    st.success(f"Added {ticker} — {new_qty:.2f} shares @ ${new_cost:.2f}")
    st.rerun()
