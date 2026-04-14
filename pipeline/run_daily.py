import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

from config import db
from data.news_fetcher import fetch_and_store_ticker_news, fetch_macro_news
from brief import generate_daily_brief

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("marketmind.pipeline")

# ── Top 50 US stocks — always fetch these regardless of user portfolios ────────
TOP_50 = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","BRK-B",
    "AVGO","JPM","LLY","V","UNH","XOM","MA","COST","HD","PG",
    "JNJ","ABBV","BAC","KO","MRK","CVX","CRM","NFLX","AMD",
    "PEP","TMO","ORCL","ACN","MCD","ADBE","LIN","QCOM","TXN",
    "WMT","DIS","INTC","IBM","GE","CAT","BA","GS","MS",
    "BKNG","SPGI","ISRG","NOW","UBER"
]


def get_user_portfolios() -> dict[str, list[str]]:
    """
    Read all users with portfolios from Firestore.
    Returns { uid: [ticker1, ticker2, ...] }
    """
    result = {}
    try:
        users = db.collection("users").stream()
        for u in users:
            holdings = (
                db.collection("users")
                  .document(u.id)
                  .collection("portfolio")
                  .stream()
            )
            tickers = [
                h.to_dict().get("ticker")
                for h in holdings
                if h.to_dict().get("ticker")
            ]
            if tickers:
                result[u.id] = tickers
                log.info(f"  User {u.id[:8]}... → {len(tickers)} holdings")
    except Exception as e:
        log.error(f"Failed to read user portfolios: {e}")
    return result


async def fetch_news_batch(tickers: list[str],
                           batch_size: int = 5,
                           delay: float = 1.0) -> dict[str, int]:
    """
    Fetch news for a list of tickers in parallel batches.
    Returns { ticker: articles_stored }
    """
    results = {}
    total   = len(tickers)

    for i in range(0, total, batch_size):
        batch = tickers[i:i + batch_size]
        log.info(f"  Batch {i // batch_size + 1}/{-(-total // batch_size)}"
                 f" — {batch}")

        tasks   = [fetch_and_store_ticker_news(t) for t in batch]
        fetched = await asyncio.gather(*tasks, return_exceptions=True)

        for ticker, result in zip(batch, fetched):
            if isinstance(result, Exception):
                log.error(f"    {ticker}: FAILED — {result}")
                results[ticker] = 0
            else:
                count = len(result) if result else 0
                results[ticker] = count
                log.info(f"    {ticker}: {count} new articles")

        # Rate limit between batches
        if i + batch_size < total:
            await asyncio.sleep(delay)

    return results


async def generate_briefs_for_all_users(
    user_portfolios: dict[str, list[str]]
) -> dict[str, bool]:
    """
    Generate daily brief for every user with a portfolio.
    Returns { uid: success }
    """
    async def _generate(uid: str) -> tuple[str, bool]:
        try:
            await generate_daily_brief(uid)
            return uid, True
        except Exception as e:
            log.error(f"  Brief failed for {uid[:8]}...: {e}")
            return uid, False

    tasks   = [_generate(uid) for uid in user_portfolios]
    outputs = await asyncio.gather(*tasks)
    return dict(outputs)


async def main():
    started = datetime.now(timezone.utc)
    log.info("=" * 60)
    log.info("MarketMind daily pipeline started")
    log.info(f"Time: {started.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    log.info("=" * 60)

    # ── Phase 1: Load user portfolios ────────────────────────────────────────
    log.info("\n[1/4] Loading user portfolios from Firestore...")
    user_portfolios = get_user_portfolios()
    log.info(f"Found {len(user_portfolios)} users with portfolios")

    # Merge user tickers with TOP_50 — deduplicated
    user_tickers = list(set(
        t for tickers in user_portfolios.values() for t in tickers
    ))
    all_tickers  = list(set(TOP_50 + user_tickers))
    log.info(f"Total unique tickers to fetch: {len(all_tickers)}")

    # ── Phase 2: Fetch news for all tickers ──────────────────────────────────
    log.info(f"\n[2/4] Fetching news for {len(all_tickers)} tickers...")
    ticker_results = await fetch_news_batch(
        all_tickers, batch_size=5, delay=1.0
    )
    total_articles = sum(ticker_results.values())
    log.info(f"Total new articles stored: {total_articles}")

    # ── Phase 3: Fetch macro/world news ──────────────────────────────────────
    log.info("\n[3/4] Fetching macro and world news...")
    try:
        macro_articles = await fetch_macro_news()
        log.info(f"Macro articles stored: {len(macro_articles)}")
    except Exception as e:
        log.error(f"Macro news fetch failed: {e}")

    # ── Phase 4: Generate briefs for all users ────────────────────────────────
    if user_portfolios:
        log.info(f"\n[4/4] Generating briefs for {len(user_portfolios)} users...")
        brief_results = await generate_briefs_for_all_users(user_portfolios)
        success = sum(1 for v in brief_results.values() if v)
        log.info(f"Briefs generated: {success}/{len(user_portfolios)}")
    else:
        log.info("\n[4/4] No users with portfolios — skipping brief generation")

    # ── Summary ───────────────────────────────────────────────────────────────
    duration = (datetime.now(timezone.utc) - started).total_seconds()
    log.info("\n" + "=" * 60)
    log.info("Pipeline complete")
    log.info(f"Duration:         {duration:.1f}s")
    log.info(f"Tickers fetched:  {len(all_tickers)}")
    log.info(f"Articles stored:  {total_articles}")
    log.info(f"Users briefed:    {len(user_portfolios)}")
    log.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
