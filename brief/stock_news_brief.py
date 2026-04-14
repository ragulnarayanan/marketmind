"""
Per-ticker news summary for the daily brief.
Model: gpt-4o-mini
Retrieves news from Qdrant, auto-fetches if stale, summarizes via LLM.
"""
import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse

from langchain_openai import ChatOpenAI
from qdrant_client.models import Direction, FieldCondition, Filter, MatchValue, OrderBy, Range

from config import GPT_FAST, OPENAI_API_KEY
from data.news_fetcher import fetch_and_store_ticker_news
from data.qdrant_client import client
from utils import parse_llm_json

_llm = ChatOpenAI(model=GPT_FAST, temperature=0.1, api_key=OPENAI_API_KEY)

_SYSTEM = """STRICT INSTRUCTION: You must ONLY use information from the \
articles provided in the user message below.
Do NOT use any prior training knowledge about {ticker} or any company.
Any price, percentage, statistic, or fact you state MUST appear \
verbatim or paraphrased directly from the provided articles.
If a fact is not in the articles, do not include it.

You are a financial news analyst. Synthesize the provided articles \
about {ticker} into a single paragraph of 3-5 sentences.

Rules:
- Every fact must come directly from the articles provided
- Mention tension or contradiction if news is mixed
- Do not pad with generic filler statements
- End with one sentence on overall sentiment based only on the articles
- Write for an investor who wants the signal not the noise

Return JSON only, no markdown:
{{
  "summary": "paragraph text here",
  "sentiment_label": "bullish|bearish|neutral",
  "sentiment_score": float 0-10
}}"""


def _format_articles_for_prompt(articles: list[dict]) -> str:
    parts = []
    for a in articles:
        source  = a.get("source_name", "")
        date    = a.get("published_date", "")
        headline = a.get("headline", "")
        content = (
            a.get("full_text", "")[:500]
            if a.get("full_text")
            else a.get("description", "")
        )
        parts.append(
            f"[Source: {source} | {date}]\n"
            f"Headline: {headline}\n"
            f"Content: {content}"
        )
    return "\n\n".join(parts)


def _is_valid_url(url: str) -> bool:
    if not url:
        return False
    bad_patterns = [
        "consent.yahoo.com",
        "consent.",
        "login.",
        "signin.",
        "subscribe.",
        "paywall.",
        "javascript:",
    ]
    return not any(p in url.lower() for p in bad_patterns)


def _extract_domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc
        return netloc.removeprefix("www.")
    except Exception:
        return ""


def _fetch_recent_articles(ticker: str) -> list[dict]:
    results, _ = client.scroll(
        "news_articles",
        scroll_filter=Filter(must=[
            FieldCondition(key="tickers", match=MatchValue(value=ticker)),
        ]),
        limit=50,
        with_payload=True,
        order_by=OrderBy(key="published_at", direction=Direction.DESC),
    )
    return [r.payload for r in results[:10]]


async def summarize_stock_news_for_brief(
    ticker: str,
    hours_back: int = 168,   # kept for signature compatibility, no longer used for filtering
) -> dict:
    """
    Retrieve the 10 most recent articles for ticker from Qdrant, ordered by
    published_at descending. If none exist, fetch from APIs and retry once.
    Summarize via GPT-4o-mini and return structured dict.
    """
    try:
        articles = await asyncio.to_thread(_fetch_recent_articles, ticker)

        # Auto-fetch if nothing found in Qdrant
        if not articles:
            await fetch_and_store_ticker_news(ticker)
            articles = await asyncio.to_thread(_fetch_recent_articles, ticker)

        if not articles:
            return {
                "ticker":          ticker,
                "summary":         "No news available for this ticker.",
                "sentiment_label": "neutral",
                "sentiment_score": 5.0,
                "article_count":   0,
                "sources":         [],
                "generated_at":    datetime.now(timezone.utc).isoformat(),
            }

        formatted = _format_articles_for_prompt(articles)
        messages = [
            {"role": "system", "content": _SYSTEM.format(ticker=ticker)},
            {"role": "user", "content": f"Articles about {ticker}:\n{formatted}"},
        ]
        response = await asyncio.to_thread(_llm.invoke, messages)
        result   = parse_llm_json(response.content.strip())

        # Sources: scroll top-50 by recency, filter valid URLs in Python
        all_results, _ = client.scroll(
            "news_articles",
            scroll_filter=Filter(must=[
                FieldCondition(key="tickers", match=MatchValue(value=ticker)),
            ]),
            limit=50,
            with_payload=True,
            order_by=OrderBy(key="published_at", direction=Direction.DESC),
        )

        sources = []
        for r in all_results:
            p   = r.payload
            url = p.get("url") or ""
            if not p.get("has_url") or not _is_valid_url(url):
                continue
            sources.append({
                "headline":    p.get("headline", ""),
                "url":         url,
                "source_name": p.get("source_name", ""),
                "domain":      _extract_domain(url),
                "published_at": p.get("published_date", ""),
                "sentiment":   p.get("sentiment_label", "neutral"),
            })

        sources = sorted(
            sources,
            key=lambda x: x.get("impact_score", 40),
            reverse=True,
        )[:5]

        top_headline = ""
        if articles:
            best = max(articles, key=lambda a: a.get("impact_score", 40))
            top_headline = best.get("headline", "")

        return {
            "ticker":          ticker,
            "summary":         result.get("summary", ""),
            "sentiment_label": result.get("sentiment_label", "neutral"),
            "sentiment_score": float(result.get("sentiment_score", 5.0)),
            "article_count":   len(articles),
            "top_headline":    top_headline,
            "sources":         sources,
            "generated_at":    datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        return {
            "ticker":          ticker,
            "summary":         f"News summary unavailable: {e}",
            "sentiment_label": "neutral",
            "sentiment_score": 5.0,
            "article_count":   0,
            "sources":         [],
            "generated_at":    datetime.now(timezone.utc).isoformat(),
        }
