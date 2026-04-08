import yfinance as yf
import streamlit as st


def get_sector(ticker: str) -> str:
    """Return sector string for a ticker via yfinance."""
    cache = st.session_state.setdefault("sector_cache", {})
    if ticker in cache:
        return cache[ticker]
    try:
        info = yf.Ticker(ticker).info
        sector = info.get("sector", "Unknown")
    except Exception:
        sector = "Unknown"
    cache[ticker] = sector
    return sector


def get_sectors_for_portfolio(holdings: list) -> dict[str, str]:
    """Return { ticker: sector } for all holdings."""
    return {h["ticker"]: get_sector(h["ticker"]) for h in holdings}
