"""
Per-ticker news summary for the daily brief.
Model: gpt-4o-mini
Retrieves news from Qdrant, auto-fetches if stale, summarizes via LLM.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from langchain_openai import ChatOpenAI

from config import BRIEF_LOOKBACK_HOURS, GPT_FAST, OPENAI_API_KEY, TOP_K_VECTOR_RESULTS
from data.news_fetcher import fetch_and_store_ticker_news
from data.qdrant_client import search_news
from utils import parse_llm_json
from utils.embeddings import embed_text

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


async def summarize_stock_news_for_brief(
    ticker: str,
    hours_back: int = 168,
) -> dict:
    """
    Retrieve news chunks for ticker from Qdrant (last hours_back hours).
    If no news in Qdrant for today, trigger fetch_and_store_ticker_news first.
    Aggregate all articles into one summary using GPT-4o-mini.
    Return structured dict.
    """
    try:
        from_unix = int(
            (datetime.now(timezone.utc) - timedelta(hours=hours_back)).timestamp()
        )
        query_vec = await asyncio.to_thread(
            embed_text, f"latest news {ticker} stock price earnings"
        )
        articles = await asyncio.to_thread(
            search_news, query_vec, [ticker], None, from_unix, TOP_K_VECTOR_RESULTS
        )

        # Auto-fetch if nothing found in Qdrant for this window
        if not articles:
            await fetch_and_store_ticker_news(ticker)
            articles = await asyncio.to_thread(
                search_news, query_vec, [ticker], None, from_unix, TOP_K_VECTOR_RESULTS
            )

        if not articles:
            return {
                "ticker":          ticker,
                "summary":         "No news available for this ticker in the last 24 hours.",
                "sentiment_label": "neutral",
                "sentiment_score": 5.0,
                "article_count":   0,
                "sources":         [],
                "generated_at":    datetime.now(timezone.utc).isoformat(),
            }

        formatted = _format_articles_for_prompt(articles)
        messages = [
            {"role": "system", "content": _SYSTEM.format(ticker=ticker)},
            {
                "role": "user",
                "content": (
                    f"Articles about {ticker} (last {hours_back} hours):\n{formatted}"
                ),
            },
        ]
        response = await asyncio.to_thread(_llm.invoke, messages)
        result   = parse_llm_json(response.content.strip())

        # Scroll ALL articles and filter in Python (no bool index needed)
        from data.qdrant_client import client
        from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

        all_results, _ = client.scroll(
            "news_articles",
            scroll_filter=Filter(must=[
                FieldCondition(key="tickers",      match=MatchValue(value=ticker)),
                FieldCondition(key="published_at", range=Range(gte=from_unix)),
            ]),
            limit=100,
            with_payload=True,
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

        return {
            "ticker":          ticker,
            "summary":         result.get("summary", ""),
            "sentiment_label": result.get("sentiment_label", "neutral"),
            "sentiment_score": float(result.get("sentiment_score", 5.0)),
            "article_count":   len(articles),
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
