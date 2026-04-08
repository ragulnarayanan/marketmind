"""
Per-ticker 24-hour news summary for the daily brief.
Model: gpt-4o-mini
"""
import asyncio
import json
from datetime import datetime, timedelta, timezone

from langchain_openai import ChatOpenAI

from config import BRIEF_LOOKBACK_HOURS, GPT_FAST, OPENAI_API_KEY, TOP_K_VECTOR_RESULTS
from data.qdrant_client import search_news
from utils.embeddings import embed_text

_llm = ChatOpenAI(model=GPT_FAST, temperature=0.1, api_key=OPENAI_API_KEY)

_SYSTEM = (
    "You are a financial news summarizer. Summarize the last 24 hours of news about "
    "{ticker} in exactly 2 sentences. State the overall sentiment and the most important "
    "development. Return JSON only, no markdown: "
    '{"summary": "<str>", "sentiment": "bullish|bearish|neutral", '
    '"top_headline": "<str>", "score": <float 0-10>}'
)


async def summarize_stock_news_for_brief(ticker: str) -> dict:
    try:
        from_unix = int(
            (datetime.now(timezone.utc) - timedelta(hours=BRIEF_LOOKBACK_HOURS)).timestamp()
        )
        query_vec = await asyncio.to_thread(
            embed_text, f"latest news {ticker} stock price movement earnings"
        )
        articles = await asyncio.to_thread(
            search_news, query_vec, [ticker], None, from_unix, TOP_K_VECTOR_RESULTS
        )

        if not articles:
            return {
                "ticker": ticker,
                "summary": "No news in the last 24 hours.",
                "sentiment": "neutral",
                "top_headline": "N/A",
                "score": 5.0,
            }

        news_text = "\n\n".join(
            f"[{a.get('published_date', '')}] {a.get('headline', '')} — {a.get('summary_2sent', '')}"
            for a in articles
        )
        messages = [
            {"role": "system", "content": _SYSTEM.format(ticker=ticker)},
            {"role": "user", "content": news_text},
        ]
        response = await asyncio.to_thread(_llm.invoke, messages)
        raw = response.content.strip()
        result = json.loads(raw)
        result["ticker"] = ticker
        return result
    except Exception as e:
        return {
            "ticker": ticker,
            "summary": f"News summary unavailable: {e}",
            "sentiment": "neutral",
            "top_headline": "N/A",
            "score": 5.0,
        }
