"""
Orchestrator: run_stock_research(ticker) -> dict
Phases:
  1. Parallel data fetch (news + SEC)
  2. Parallel agents 1-3 (news, sec, financials)
  3. Sequential: synthesis -> verdict
"""
import asyncio
from datetime import datetime

from agents.financials_agent import run_financials_agent
from agents.news_agent import run_news_agent
from agents.sec_agent import run_sec_agent
from agents.synthesis_agent import run_synthesis_agent
from agents.verdict_agent import run_verdict_agent
from data.news_fetcher import fetch_and_store_ticker_news
from data.sec_fetcher import fetch_and_embed_sec_filing


async def run_stock_research(ticker: str) -> dict:
    ticker = ticker.upper().strip()

    # Phase 1: parallel data fetch
    await asyncio.gather(
        fetch_and_store_ticker_news(ticker),
        asyncio.to_thread(fetch_and_embed_sec_filing, ticker),
    )

    # Phase 2: agents 1-3 in parallel
    news_r, sec_r, fin_r = await asyncio.gather(
        run_news_agent(ticker),
        run_sec_agent(ticker),
        run_financials_agent(ticker),
    )

    # Phase 3: synthesis then verdict (sequential)
    synth   = await run_synthesis_agent(ticker, news_r, sec_r, fin_r)
    verdict = await run_verdict_agent(ticker, synth)

    return {
        "ticker": ticker,
        "news": news_r,
        "sec": sec_r,
        "financials": fin_r,
        "synthesis": synth,
        "verdict": verdict,
        "generated_at": datetime.utcnow().isoformat(),
    }
