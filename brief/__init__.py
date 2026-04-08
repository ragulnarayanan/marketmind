"""
Daily Brief orchestrator: generate_daily_brief(uid) -> dict
"""
import asyncio
from datetime import datetime

from brief.buy_wait_signal import generate_signal
from brief.macro_filter import get_relevant_macro_news
from brief.portfolio_pnl import compute_portfolio_snapshot
from brief.stock_news_brief import summarize_stock_news_for_brief
from data.firestore_client import (
    get_portfolio,
    get_todays_brief,
    get_watchlist,
    store_brief,
)
from data.news_fetcher import fetch_and_store_ticker_news, fetch_macro_news


async def generate_daily_brief(uid: str) -> dict:
    cached = get_todays_brief(uid)
    if cached:
        return cached

    portfolio = get_portfolio(uid)
    watchlist = get_watchlist(uid)

    if not portfolio:
        return {
            "empty": True,
            "message": "Add stocks to your portfolio to get a daily brief.",
        }

    tickers = [h["ticker"] for h in portfolio]

    # Phase 1: parallel news fetch
    await asyncio.gather(
        asyncio.gather(*[fetch_and_store_ticker_news(t) for t in tickers + watchlist]),
        fetch_macro_news(),
    )

    # Phase 2: P&L + per-stock news + macro in parallel
    pnl_task   = asyncio.to_thread(compute_portfolio_snapshot, portfolio)
    news_tasks = asyncio.gather(*[summarize_stock_news_for_brief(t) for t in tickers])
    macro_task = get_relevant_macro_news(portfolio, watchlist)

    pnl, news_list, macro = await asyncio.gather(pnl_task, news_tasks, macro_task)
    news_by_ticker = {s["ticker"]: s for s in news_list}

    # Phase 3: buy/wait signals per holding
    holding_details = []
    for h in portfolio:
        pnl_row = next((r for r in pnl.get("holdings", []) if r["ticker"] == h["ticker"]), {})
        holding_details.append({**h, **pnl_row})

    signals_list = await asyncio.gather(*[
        generate_signal(h, news_by_ticker.get(h["ticker"], {}), macro)
        for h in holding_details
    ])
    signals = {s["ticker"]: s for s in signals_list}

    brief = {
        "generated_at": datetime.utcnow().isoformat(),
        "portfolio_snapshot": pnl,
        "stock_news": news_by_ticker,
        "macro_alerts": macro,
        "signals": signals,
    }

    store_brief(uid, brief)
    return brief
