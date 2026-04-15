"""
Daily Brief orchestrator: generate_daily_brief(uid) -> dict
"""
import asyncio
from datetime import datetime
from urllib.parse import urlparse

from qdrant_client.models import Direction, FieldCondition, Filter, MatchValue, OrderBy

from brief.buy_wait_signal import generate_signal
from brief.macro_news_brief import get_macro_alerts_for_portfolio
from brief.portfolio_news_summary import generate_portfolio_summary
from brief.portfolio_pnl import compute_portfolio_snapshot
from data.firestore_client import (
    get_portfolio,
    get_todays_brief,
    store_brief,
)
from data.news_fetcher import fetch_and_store_ticker_news, fetch_macro_news
from data.qdrant_client import client

_BAD_URL_PATTERNS = [
    "consent.yahoo.com", "consent.", "login.",
    "signin.", "subscribe.", "paywall.", "javascript:",
]


def _is_valid_url(url: str) -> bool:
    if not url:
        return False
    return not any(p in url.lower() for p in _BAD_URL_PATTERNS)


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.removeprefix("www.")
    except Exception:
        return ""


async def generate_daily_brief(uid: str) -> dict:
    cached = get_todays_brief(uid)
    if cached:
        return cached

    portfolio = get_portfolio(uid)

    if not portfolio:
        return {
            "empty":   True,
            "message": "Add stocks to your portfolio to get a daily brief.",
        }

    tickers = [h["ticker"] for h in portfolio]

    # Phase 1: fetch all news in parallel
    await asyncio.gather(
        asyncio.gather(*[fetch_and_store_ticker_news(t) for t in tickers]),
        fetch_macro_news(),
    )

    # Phase 2: compute P&L
    pnl = await asyncio.to_thread(compute_portfolio_snapshot, portfolio)
    holdings_with_prices = pnl["holdings"]

    # Fetch news articles per ticker from Qdrant (10 most recent each)
    news_by_ticker: dict[str, list] = {}
    for ticker in tickers:
        results, _ = client.scroll(
            "news_articles",
            scroll_filter=Filter(must=[
                FieldCondition(key="tickers", match=MatchValue(value=ticker)),
            ]),
            limit=10,
            with_payload=True,
            order_by=OrderBy(key="published_at", direction=Direction.DESC),
        )
        news_by_ticker[ticker] = [r.payload for r in results]

    # Phase 3: portfolio summary + macro alerts + signals in parallel
    portfolio_summary, macro_alerts, signals_list = await asyncio.gather(
        generate_portfolio_summary(holdings_with_prices, news_by_ticker),
        get_macro_alerts_for_portfolio(holdings_with_prices),
        asyncio.gather(*[
            generate_signal(h, news_by_ticker.get(h["ticker"], []), [])
            for h in holdings_with_prices
        ]),
    )

    # Collect source links — separate wider scroll per ticker (top 50),
    # filtered in Python for has_url=True. This avoids missing URLs when
    # the top-10 summary articles happen to all be Finnhub (no URL).
    all_sources = []
    for ticker in tickers:
        source_results, _ = client.scroll(
            "news_articles",
            scroll_filter=Filter(must=[
                FieldCondition(key="tickers", match=MatchValue(value=ticker)),
                FieldCondition(key="has_url", match=MatchValue(value=True)),
            ]),
            limit=15,
            with_payload=True,
            order_by=OrderBy(key="published_at", direction=Direction.DESC),
        )
        for r in source_results:
            a   = r.payload
            url = a.get("url") or ""
            if not a.get("has_url") or not url or not _is_valid_url(url):
                continue
            all_sources.append({
                "headline":    a.get("headline", ""),
                "url":         url,
                "source_name": a.get("source_name", ""),
                "domain":      _extract_domain(url),
                "published_at": a.get("published_date", ""),
                "ticker":      ticker,
            })

    seen_urls: set[str] = set()
    unique_sources = []
    for s in all_sources:
        if s["url"] not in seen_urls:
            seen_urls.add(s["url"])
            unique_sources.append(s)
    unique_sources = unique_sources[:15]

    signals = {s["ticker"]: s for s in signals_list}

    brief = {
        "generated_at":       datetime.utcnow().isoformat(),
        "portfolio_snapshot": pnl,
        "portfolio_summary":  portfolio_summary,
        "macro_alerts":       macro_alerts,
        "signals":            signals,
        "sources":            unique_sources,
    }

    store_brief(uid, brief)
    return brief
