"""
Macro news alerts scored for portfolio relevance.
Model: gpt-4o. Reads macro articles already stored in Qdrant by fetch_macro_news().
"""
import asyncio

from langchain_openai import ChatOpenAI
from qdrant_client.models import Direction, FieldCondition, Filter, MatchValue, OrderBy

from config import GPT_SMART, OPENAI_API_KEY
from data.qdrant_client import client
from utils import parse_llm_json
from utils.sector_mapper import get_sectors_for_portfolio

_llm = ChatOpenAI(model=GPT_SMART, temperature=0.1, api_key=OPENAI_API_KEY)

_MACRO_SYSTEM = """You are a portfolio risk analyst.

The investor holds: {holdings_summary}
Their sector exposure: {sectors_summary}

Review these macro headlines. For each one score it 0-10 for \
relevance to this specific portfolio. Return ONLY items scoring 6+.

For each relevant item explain in ONE sentence exactly which \
holding it affects and how (bullish or bearish).

Return JSON array only:
[
  {{
    "headline": "headline text",
    "source": "source name",
    "url": "url or null",
    "relevance_score": int,
    "why_matters": "one sentence — mention specific ticker",
    "impact": "bullish|bearish|neutral",
    "published_date": "YYYY-MM-DD"
  }}
]

If no headlines score 6+, return empty array []."""


async def get_macro_alerts_for_portfolio(
    holdings: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """
    Scroll the most recent 30 macro articles from Qdrant (already fetched by
    fetch_macro_news), score them for portfolio relevance using GPT-4o,
    and return top_n items scoring 6+.
    """
    if not holdings:
        return []

    try:
        # Scroll most recent 30 macro articles from Qdrant
        results, _ = await asyncio.to_thread(
            lambda: client.scroll(
                "news_articles",
                scroll_filter=Filter(must=[
                    FieldCondition(key="sectors", match=MatchValue(value="macro")),
                ]),
                limit=30,
                with_payload=True,
                order_by=OrderBy(key="published_at", direction=Direction.DESC),
            )
        )
        articles = [r.payload for r in results]

        if not articles:
            return []

        # Build portfolio context
        holdings_summary = ", ".join(
            f"{h['ticker']} ({h.get('qty', 0):.0f} shares)"
            for h in holdings
        )
        sectors_map  = await asyncio.to_thread(get_sectors_for_portfolio, holdings)
        sectors_list = list(set(sectors_map.values()))
        sectors_summary = ", ".join(sectors_list) or "Technology"

        # Format headlines for the prompt
        headlines_text = "\n\n".join(
            f"[{a.get('source_name', 'Unknown')}] {a.get('headline', '')} "
            f"({a.get('published_date', '')}) — {a.get('description', '')[:150]}"
            for a in articles
        )

        prompt = _MACRO_SYSTEM.format(
            holdings_summary=holdings_summary,
            sectors_summary=sectors_summary,
        )
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user",   "content": f"Headlines:\n\n{headlines_text}"},
        ]

        response = await asyncio.to_thread(_llm.invoke, messages)
        result   = parse_llm_json(response.content.strip())

        if not isinstance(result, list):
            return []

        # Sort by relevance_score desc, return top_n
        return sorted(result, key=lambda x: x.get("relevance_score", 0), reverse=True)[:top_n]

    except Exception:
        return []
