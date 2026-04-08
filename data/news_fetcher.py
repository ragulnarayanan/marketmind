"""
Fetch news from NewsAPI + Finnhub, deduplicate via content hash,
embed, and store in Qdrant.
"""
import asyncio
import hashlib
import time
from datetime import datetime, timedelta, timezone

import aiohttp
import finnhub
from newsapi import NewsApiClient

from config import (
    BRIEF_LOOKBACK_HOURS,
    FINNHUB_API_KEY,
    NEWS_LOOKBACK_DAYS,
    NEWSAPI_KEY,
)
from data.qdrant_client import upsert_news_article
from utils.embeddings import embed_text
from utils.sector_mapper import get_sector

_newsapi = NewsApiClient(api_key=NEWSAPI_KEY)
_finnhub = finnhub.Client(api_key=FINNHUB_API_KEY)


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _build_article_payload(
    headline: str,
    summary: str,
    source: str,
    url: str,
    published_at: datetime,
    tickers: list[str],
    sectors: list[str],
) -> dict:
    content_text = f"{headline} {summary}"
    return {
        "article_id": _content_hash(url or content_text),
        "headline": headline,
        "summary_2sent": summary[:500],
        "source": source,
        "tickers": tickers,
        "sectors": sectors,
        "sentiment_label": "neutral",
        "sentiment_score": 0.5,
        "impact_score": 50,
        "published_at": int(published_at.timestamp()),
        "published_date": published_at.strftime("%Y-%m-%d"),
        "content_hash": _content_hash(content_text),
    }


async def fetch_and_store_ticker_news(ticker: str) -> int:
    """Fetch last NEWS_LOOKBACK_DAYS of news for ticker, embed, store. Returns article count."""
    articles = []

    # NewsAPI
    try:
        from_date = (datetime.now(timezone.utc) - timedelta(days=NEWS_LOOKBACK_DAYS)).strftime(
            "%Y-%m-%d"
        )
        resp = await asyncio.to_thread(
            _newsapi.get_everything,
            q=ticker,
            from_param=from_date,
            language="en",
            sort_by="publishedAt",
            page_size=20,
        )
        sector = await asyncio.to_thread(get_sector, ticker)
        for a in resp.get("articles", []):
            if not a.get("title") or a["title"] == "[Removed]":
                continue
            try:
                pub = datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00"))
            except Exception:
                pub = datetime.now(timezone.utc)
            articles.append(
                _build_article_payload(
                    headline=a["title"],
                    summary=a.get("description") or a.get("content") or "",
                    source=a.get("source", {}).get("name", "NewsAPI"),
                    url=a.get("url", ""),
                    published_at=pub,
                    tickers=[ticker],
                    sectors=[sector],
                )
            )
    except Exception:
        pass

    # Finnhub
    try:
        from_ts = int(
            (datetime.now(timezone.utc) - timedelta(days=NEWS_LOOKBACK_DAYS)).timestamp()
        )
        to_ts = int(datetime.now(timezone.utc).timestamp())
        fh_news = await asyncio.to_thread(
            _finnhub.company_news, ticker, _date(from_ts), _date(to_ts)
        )
        sector = await asyncio.to_thread(get_sector, ticker)
        for a in (fh_news or []):
            if not a.get("headline"):
                continue
            pub = datetime.fromtimestamp(a.get("datetime", time.time()), tz=timezone.utc)
            articles.append(
                _build_article_payload(
                    headline=a["headline"],
                    summary=a.get("summary", ""),
                    source=a.get("source", "Finnhub"),
                    url=a.get("url", ""),
                    published_at=pub,
                    tickers=[ticker],
                    sectors=[sector],
                )
            )
    except Exception:
        pass

    # Deduplicate by content_hash then embed + store
    seen: set[str] = set()
    stored = 0
    for article in articles:
        ch = article["content_hash"]
        if ch in seen:
            continue
        seen.add(ch)
        try:
            text_to_embed = f"{article['headline']} {article['summary_2sent']}"
            vector = await asyncio.to_thread(embed_text, text_to_embed)
            await asyncio.to_thread(upsert_news_article, article, vector)
            stored += 1
        except Exception:
            pass

    return stored


async def fetch_macro_news() -> int:
    """Fetch broad macro / market news and store in Qdrant without ticker filter."""
    articles = []
    macro_queries = [
        "Federal Reserve interest rates monetary policy",
        "inflation CPI economic data",
        "stock market S&P 500 rally selloff",
        "earnings season corporate profits",
        "geopolitical risk global economy",
    ]

    for query in macro_queries:
        try:
            from_date = (
                datetime.now(timezone.utc) - timedelta(hours=BRIEF_LOOKBACK_HOURS)
            ).strftime("%Y-%m-%d")
            resp = await asyncio.to_thread(
                _newsapi.get_everything,
                q=query,
                from_param=from_date,
                language="en",
                sort_by="publishedAt",
                page_size=10,
            )
            for a in resp.get("articles", []):
                if not a.get("title") or a["title"] == "[Removed]":
                    continue
                try:
                    pub = datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00"))
                except Exception:
                    pub = datetime.now(timezone.utc)
                articles.append(
                    _build_article_payload(
                        headline=a["title"],
                        summary=a.get("description") or "",
                        source=a.get("source", {}).get("name", "NewsAPI"),
                        url=a.get("url", ""),
                        published_at=pub,
                        tickers=[],
                        sectors=["macro"],
                    )
                )
        except Exception:
            pass

    seen: set[str] = set()
    stored = 0
    for article in articles:
        ch = article["content_hash"]
        if ch in seen:
            continue
        seen.add(ch)
        try:
            text_to_embed = f"{article['headline']} {article['summary_2sent']}"
            vector = await asyncio.to_thread(embed_text, text_to_embed)
            await asyncio.to_thread(upsert_news_article, article, vector)
            stored += 1
        except Exception:
            pass

    return stored


def _date(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
