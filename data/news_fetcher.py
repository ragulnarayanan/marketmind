"""
Fetch news from Finnhub + NewsAPI, scrape full text via trafilatura,
deduplicate via content hash, embed, and store in Qdrant.
"""
import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import finnhub
import requests as _requests
import trafilatura
from newsapi import NewsApiClient

from config import (
    BRIEF_LOOKBACK_HOURS,
    FINNHUB_API_KEY,
    NEWS_LOOKBACK_DAYS,
    NEWSAPI_KEY,
)
from data.qdrant_client import hash_exists, upsert_news_article
from utils.embeddings import embed_text
from utils.sector_mapper import get_sector

_newsapi  = NewsApiClient(api_key=NEWSAPI_KEY)
_finnhub  = finnhub.Client(api_key=FINNHUB_API_KEY)
_SCRAPE_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MarketMind/1.0)"}

# ── Sentiment word lists ──────────────────────────────────────────────────────

BULLISH_WORDS = [
    "beat", "beats", "record", "growth", "upgrade", "raises",
    "surges", "jumps", "strong", "profit", "gains", "positive",
    "outperform", "buy", "bullish", "rally",
]
BEARISH_WORDS = [
    "miss", "misses", "decline", "downgrade", "cuts", "drops",
    "falls", "weak", "loss", "layoffs", "lawsuit", "recall",
    "investigation", "bearish", "sell", "concern", "risk",
]

_PREMIUM_SOURCES = {
    "reuters", "bloomberg", "wall street journal", "wsj",
    "financial times", "ft", "barron's", "cnbc", "marketwatch",
}
_EARNINGS_WORDS = ["earnings", "guidance", "revenue", "eps", "quarterly", "results"]
_CEO_WORDS      = ["ceo", "cfo", "executive", "president", "chief", "officer"]
_MA_WORDS       = ["acquisition", "merger", "acquires", "buyout", "takeover", "deal"]


# ── Pure helper functions ─────────────────────────────────────────────────────

BOILERPLATE_SIGNALS = [
    "if you click 'accept all'",
    "iab transparency",
    "we and our partners",
    "cookie policy",
    "consent framework",
    "store and / or access information on a device",
]


_BAD_URL_PATTERNS = [
    "consent.yahoo.com",
    "consent.",
    "login.",
    "signin.",
    "subscribe.",
    "paywall.",
    "javascript:",
]


def _is_valid_url(url: str) -> bool:
    if not url:
        return False
    return not any(p in url.lower() for p in _BAD_URL_PATTERNS)


def _is_boilerplate(text: str) -> bool:
    if not text:
        return True
    text_lower = text.lower()
    return any(signal in text_lower for signal in BOILERPLATE_SIGNALS)


def _compute_hash(title: str, source: str, published_date: str) -> str:
    """sha256(title + source + published_date)"""
    return hashlib.sha256(f"{title}{source}{published_date}".encode()).hexdigest()


def _scrape_full_text(url: str, timeout: int = 8) -> str | None:
    """
    Attempt full article extraction using trafilatura.
    Returns clean text string or None on failure.
    Never raises.
    """
    try:
        response = _requests.get(url, timeout=timeout, headers=_SCRAPE_HEADERS)
        if not response.ok:
            return None
        text = trafilatura.extract(response.text)
        if not text or _is_boilerplate(text):
            return None
        return text
    except Exception:
        return None


def _build_embed_text(title: str, description: str, full_text: str | None) -> str:
    """Combine title + description + full_text[:1000] for embedding."""
    parts = [title]
    if description and not _is_boilerplate(description):
        parts.append(description)
    if full_text:
        parts.append(full_text[:1000])
    return " ".join(parts)


def _basic_sentiment(title: str, description: str) -> tuple[str, float]:
    """
    Returns (sentiment_label, sentiment_score).
    Score: normalize bullish - bearish keyword count to 0-10.
    """
    text = f"{title} {description}".lower()
    b = sum(1 for w in BULLISH_WORDS if w in text)
    e = sum(1 for w in BEARISH_WORDS if w in text)
    score = max(0.0, min(10.0, 5.0 + (b - e) * 0.5))
    if score > 5.5:
        label = "bullish"
    elif score < 4.5:
        label = "bearish"
    else:
        label = "neutral"
    return label, round(score, 1)


def _impact_score(title: str, source_name: str) -> int:
    """Rough 0-100 relevance score based on source tier and headline keywords."""
    score = 40
    t = title.lower()
    s = source_name.lower()
    if any(p in s for p in _PREMIUM_SOURCES):
        score += 30
    if any(w in t for w in _EARNINGS_WORDS):
        score += 20
    if any(w in t for w in _CEO_WORDS):
        score += 15
    if any(w in t for w in _MA_WORDS):
        score += 20
    return min(score, 100)


def _build_payload(
    title: str,
    description: str,
    full_text: str | None,
    url: str | None,
    has_url: bool,
    source_name: str,
    tickers: list[str],
    sectors: list[str],
    published_at: datetime,
    source_api: str,
) -> dict:
    published_date = published_at.strftime("%Y-%m-%d")
    sentiment_label, sentiment_score = _basic_sentiment(title, description)
    return {
        "article_id":      str(uuid4()),
        "headline":        title,
        "description":     description[:500],
        "full_text":       full_text,
        "url":             url,
        "has_url":         has_url,
        "source_name":     source_name,
        "tickers":         tickers,
        "sectors":         sectors,
        "sentiment_label": sentiment_label,
        "sentiment_score": sentiment_score,
        "impact_score":    _impact_score(title, source_name),
        "published_at":    int(published_at.timestamp()),
        "published_date":  published_date,
        "source_api":      source_api,
        "has_full_text":   full_text is not None,
        "content_hash":    _compute_hash(title, source_name, published_date),
    }


# ── Shared dedup + upsert ─────────────────────────────────────────────────────

async def _store_articles(raw_articles: list[dict]) -> list[dict]:
    """Dedup against Qdrant, embed, and upsert. Returns list of newly stored payloads."""
    stored = []
    seen: set[str] = set()
    for article in raw_articles:
        ch = article["content_hash"]
        if ch in seen:
            continue
        seen.add(ch)
        try:
            if await asyncio.to_thread(hash_exists, ch):
                continue
            vector = await asyncio.to_thread(
                embed_text,
                _build_embed_text(article["headline"], article["description"], article.get("full_text")),
            )
            await asyncio.to_thread(upsert_news_article, article, vector)
            stored.append(article)
        except Exception:
            pass
    return stored


# ── Public API ────────────────────────────────────────────────────────────────

async def fetch_and_store_ticker_news(
    ticker: str,
    since: datetime | None = None,
) -> list[dict]:
    """
    Fetch last 7 days of news for a ticker from Finnhub + NewsAPI.
    If since is provided, only fetch articles published after that datetime.
    Scrape full text via trafilatura (best effort).
    Embed and store in Qdrant. Return list of stored article dicts.
    """
    cutoff     = since or (datetime.now(timezone.utc) - timedelta(days=NEWS_LOOKBACK_DAYS))
    sector     = await asyncio.to_thread(get_sector, ticker)
    from_date  = (datetime.now() - timedelta(days=NEWS_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    to_date    = datetime.now().strftime("%Y-%m-%d")
    raw: list[dict] = []

    # ── NewsAPI (primary — real scrapeable URLs) ───────────────────────────────
    try:
        resp = await asyncio.to_thread(
            _newsapi.get_everything,
            q=ticker,
            from_param=cutoff.strftime("%Y-%m-%d"),
            language="en",
            sort_by="publishedAt",
            page_size=20,
        )
        for a in resp.get("articles", []):
            title = (a.get("title") or "").strip()
            url   = (a.get("url")   or "").strip()
            if not title or not url or title == "[Removed]":
                continue
            try:
                pub = datetime.strptime(
                    a.get("publishedAt", ""), "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=timezone.utc)
            except Exception:
                pub = datetime.now(timezone.utc)
            if pub < cutoff:
                continue
            description = a.get("description") or a.get("content") or ""
            valid = _is_valid_url(url)
            full_text = await asyncio.to_thread(_scrape_full_text, url) if valid else None
            raw.append(_build_payload(
                title=title,
                description=description,
                full_text=full_text,
                url=url if valid else None,
                has_url=valid,
                source_name=(a.get("source") or {}).get("name", "NewsAPI"),
                tickers=[ticker],
                sectors=[sector],
                published_at=pub,
                source_api="newsapi",
            ))
    except Exception:
        pass

    # ── Finnhub (secondary — headline + summary only, no usable URL) ──────────
    try:
        fh_news = await asyncio.to_thread(
            _finnhub.company_news, ticker, _from=from_date, to=to_date
        )
        for a in (fh_news or []):
            title = (a.get("headline") or "").strip()
            if not title:
                continue
            pub_ts = a.get("datetime")
            if not pub_ts:
                continue
            pub = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
            if pub < cutoff:
                continue
            raw.append(_build_payload(
                title=title,
                description=a.get("summary", ""),
                full_text=None,          # no scraping — Finnhub URLs are unusable
                url=None,
                has_url=False,
                source_name=a.get("source", "Finnhub"),
                tickers=[ticker],
                sectors=[sector],
                published_at=pub,
                source_api="finnhub",
            ))
    except Exception:
        pass

    return await _store_articles(raw)


async def fetch_macro_news() -> list[dict]:
    """
    Fetch general market/macro news from NewsAPI.
    Queries: 'stock market', 'Federal Reserve', 'inflation', 'earnings'
    No ticker filter — stored with tickers=[] and sectors=['macro'].
    Return list of stored article dicts.
    """
    from_date = (
        datetime.now(timezone.utc) - timedelta(hours=BRIEF_LOOKBACK_HOURS)
    ).strftime("%Y-%m-%d")
    macro_queries = ["stock market", "Federal Reserve", "inflation", "earnings"]
    raw: list[dict] = []

    for query in macro_queries:
        try:
            resp = await asyncio.to_thread(
                _newsapi.get_everything,
                q=query,
                from_param=from_date,
                language="en",
                sort_by="publishedAt",
                page_size=10,
            )
            for a in resp.get("articles", []):
                title = (a.get("title") or "").strip()
                url   = (a.get("url")   or "").strip()
                if not title or not url or title == "[Removed]":
                    continue
                try:
                    pub = datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00"))
                except Exception:
                    pub = datetime.now(timezone.utc)
                description = a.get("description") or ""
                valid = _is_valid_url(url)
                full_text = await asyncio.to_thread(_scrape_full_text, url) if valid else None
                raw.append(_build_payload(
                    title=title,
                    description=description,
                    full_text=full_text,
                    url=url if valid else None,
                    has_url=valid,
                    source_name=(a.get("source") or {}).get("name", "NewsAPI"),
                    tickers=[],
                    sectors=["macro"],
                    published_at=pub,
                    source_api="newsapi",
                ))
        except Exception:
            pass

    return await _store_articles(raw)
