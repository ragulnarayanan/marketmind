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

_SYSTEM = """\
You are a financial news analyst writing a daily stock brief.
Synthesize the following news articles about {ticker} into a single
coherent paragraph of 3-5 sentences.

IMPORTANT: Only summarize the articles provided below.
Do not use any prior knowledge about this company.
If the articles are insufficient, say so explicitly.

Rules:
- Cover the most important developments only
- Explicitly mention tension or contradiction if news is mixed
  (e.g. "earnings beat but margin compression offset gains")
- Do not pad with generic statements
- End with one sentence on overall market sentiment for this stock
- Write for an investor who wants the signal, not the noise

Return JSON only:
{{
  "summary": "paragraph text",
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


def _extract_domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc
        return netloc.removeprefix("www.")
    except Exception:
        return ""


async def summarize_stock_news_for_brief(
    ticker: str,
    hours_back: int = 24,
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

        # Build top-5 sources — only articles with real URLs (NewsAPI), sorted by impact_score
        url_articles = [a for a in articles if a.get("has_url") and a.get("url")]
        top_articles = sorted(
            url_articles, key=lambda a: a.get("impact_score", 40), reverse=True
        )[:5]
        sources = []
        for a in top_articles:
            url    = a.get("url", "")
            pub_ts = a.get("published_at")
            pub_str = (
                datetime.fromtimestamp(pub_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
                if pub_ts else ""
            )
            sources.append({
                "headline":    a.get("headline", ""),
                "url":         url,
                "source_name": a.get("source_name", ""),
                "domain":      _extract_domain(url),
                "published_at": pub_str,
                "sentiment":   a.get("sentiment_label", "neutral"),
            })

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
