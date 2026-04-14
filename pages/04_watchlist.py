"""
Page 4 — Watchlist
Manage watched tickers with live price, daily %, and volume spike flag.
"""
import os

import streamlit as st
import yfinance as yf

from data.firestore_client import add_to_watchlist, get_watchlist, remove_from_watchlist
from utils.ui_components import green_badge, neutral_badge, pct_colored, section_header
from utils.volume_analyzer import detect_volume_spikes

st.set_page_config(page_title="Watchlist | MarketMind", layout="wide")


@st.cache_data(ttl=60, show_spinner=False)
def _ticker_price(ticker: str) -> tuple[float, float]:
    """Returns (price, daily_pct). Cached 60 s."""
    info  = yf.Ticker(ticker).fast_info
    price = round(float(info["lastPrice"] or 0), 2)
    prev  = round(float(info["previousClose"] or price), 2)
    daily = round((price - prev) / prev * 100, 2) if prev else 0.0
    return price, daily


@st.cache_data(ttl=300, show_spinner=False)
def _ticker_spikes(ticker: str) -> list:
    """Volume spikes cached 5 min."""
    return detect_volume_spikes(ticker, lookback_days=14)

uid = st.session_state.get("uid")
if not uid:
    st.warning("Please log in from the home page.")
    st.stop()

st.title("Watchlist")

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

watchlist = get_watchlist(uid)

# ── Add ticker ────────────────────────────────────────────────────────────────
sel_idx = st.selectbox(
    "Select stock to add",
    range(len(TOP_50)),
    format_func=lambda i: f"{TOP_50[i]['symbol']} — {TOP_50[i]['name']}",
    key="wl_stock_sel",
)
selected = TOP_50[sel_idx]

# Logo + name + Add button in one row
logo_col, name_col, btn_col = st.columns([1, 6, 1])
with logo_col:
    logo_path = f"assets/logos/{selected['symbol']}.svg"
    if os.path.exists(logo_path):
        svg = open(logo_path).read()
        st.markdown(f'<div style="width:48px;height:48px">{svg}</div>', unsafe_allow_html=True)
with name_col:
    st.markdown(f"**{selected['name']}** &nbsp; `{selected['symbol']}`")
with btn_col:
    if st.button("Add", type="primary", use_container_width=True):
        ticker = selected["symbol"]
        add_to_watchlist(uid, ticker)
        st.success(f"Added {ticker} to watchlist.")
        st.rerun()

# ── Watchlist table ───────────────────────────────────────────────────────────
if not watchlist:
    st.info("Your watchlist is empty. Add tickers above.")
    st.stop()

st.markdown("---")
st.markdown(section_header("Watching"), unsafe_allow_html=True)

header = st.columns([2, 1, 1, 1, 2])
for col, label in zip(header, ["Ticker", "Price", "Daily %", "Volume", "Actions"]):
    col.markdown(f"**{label}**")

for ticker in watchlist:
    cols = st.columns([2, 1, 1, 1, 2])
    cols[0].write(ticker)

    try:
        price, daily = _ticker_price(ticker)
        cols[1].write(f"${price:.2f}")
        cols[2].markdown(pct_colored(daily), unsafe_allow_html=True)
    except Exception:
        cols[1].write("N/A")
        cols[2].write("N/A")

    # Volume spike badge
    try:
        spikes       = _ticker_spikes(ticker)
        recent_spike = any(s.get("spike_ratio", 0) >= 2.0 for s in spikes)
        cols[3].markdown(green_badge("Spike") if recent_spike else neutral_badge("—"), unsafe_allow_html=True)
    except Exception:
        cols[3].write("—")

    action_col = cols[4]
    btn_col1, btn_col2 = action_col.columns(2)
    if btn_col1.button("Research", key=f"research_{ticker}"):
        st.session_state["research_ticker_input"] = ticker
        st.switch_page("pages/02_stock_research.py")
    if btn_col2.button("Remove", key=f"remove_{ticker}"):
        remove_from_watchlist(uid, ticker)
        st.rerun()
