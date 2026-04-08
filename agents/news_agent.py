"""
Agent 1 — News Analyst
Model: gpt-4o-mini
Sources: Qdrant (pre-stored NewsAPI + Finnhub articles)
"""
import asyncio
import json
from datetime import datetime, timedelta, timezone

from langchain_openai import ChatOpenAI

from config import GPT_FAST, NEWS_LOOKBACK_DAYS, OPENAI_API_KEY, TOP_K_VECTOR_RESULTS
from data.qdrant_client import search_news
from utils.embeddings import embed_text

_llm = ChatOpenAI(model=GPT_FAST, temperature=0.1, api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """You are a financial news analyst. Analyze news articles about {ticker} \
from the last 7 days. Return JSON only, no markdown, no explanation:
{{
  "sentiment_label": "bullish|bearish|neutral",
  "sentiment_score": <float 0-10>,
  "summary": "<2-3 sentence narrative of key themes>",
  "top_headline": "<single most market-moving headline>",
  "key_events": ["<event with date>"],
  "risks": ["<risk>"]
}}"""


async def run_news_agent(ticker: str) -> dict:
    try:
        from_unix = int(
            (datetime.now(timezone.utc) - timedelta(days=NEWS_LOOKBACK_DAYS)).timestamp()
        )
        query_vec = await asyncio.to_thread(
            embed_text, f"stock news sentiment {ticker} earnings revenue"
        )
        articles = await asyncio.to_thread(
            search_news,
            query_vec,
            [ticker],
            None,
            from_unix,
            TOP_K_VECTOR_RESULTS,
        )

        if not articles:
            return _empty(ticker, "No recent news found.")

        news_text = "\n\n".join(
            f"[{a.get('published_date', 'unknown')}] {a.get('headline', '')} — {a.get('summary_2sent', '')}"
            for a in articles
        )

        prompt = SYSTEM_PROMPT.format(ticker=ticker)
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"News articles for {ticker}:\n\n{news_text}"},
        ]
        response = await asyncio.to_thread(
            _llm.invoke, [{"role": m["role"], "content": m["content"]} for m in messages]
        )
        raw = response.content.strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_response": raw, "error": "JSON parse failed"}
    except Exception as e:
        return _empty(ticker, str(e))


def _empty(ticker: str, reason: str) -> dict:
    return {
        "sentiment_label": "neutral",
        "sentiment_score": 5.0,
        "summary": reason,
        "top_headline": "N/A",
        "key_events": [],
        "risks": [],
    }
