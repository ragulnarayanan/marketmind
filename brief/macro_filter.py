"""
Macro news filter for the daily brief.
Model: gemini-1.5-pro
Fetches top-15 semantic macro matches from Qdrant, scores each for portfolio relevance.
"""
import asyncio
import json
from datetime import datetime, timedelta, timezone

from langchain_google_genai import ChatGoogleGenerativeAI

from config import BRIEF_LOOKBACK_HOURS, GEMINI_PRO, GOOGLE_API_KEY, MACRO_RELEVANCE_MIN
from data.qdrant_client import search_news
from utils.embeddings import embed_text
from utils.sector_mapper import get_sectors_for_portfolio

_llm = ChatGoogleGenerativeAI(
    model=GEMINI_PRO, temperature=0.1, google_api_key=GOOGLE_API_KEY
)

_SYSTEM = """The user holds: {holdings_summary} (sectors: {sectors}).
Review these macro headlines. Score each 0-10 for relevance to this portfolio.
Return ONLY items scoring {min_score} or higher.
For each, explain in one sentence why it matters to their specific holdings.
Return a JSON array (empty array if none qualify):
[{{"headline": "<str>", "source": "<str>", "relevance_score": <int>,
   "why_matters": "<str>", "impact_direction": "positive|negative|neutral"}}]"""


async def get_relevant_macro_news(
    portfolio: list[dict],
    watchlist: list[str] | None = None,
) -> list[dict]:
    if not portfolio:
        return []

    try:
        portfolio_tickers = [h["ticker"] for h in portfolio]
        exclude_tickers   = portfolio_tickers + (watchlist or [])
        sectors_map       = await asyncio.to_thread(get_sectors_for_portfolio, portfolio)
        sectors_list      = list(set(sectors_map.values()))

        holdings_summary = ", ".join(
            f"{h['ticker']} ({h.get('qty', 0):.0f} shares)"
            for h in portfolio
        )
        sectors_str = ", ".join(sectors_list)

        from_unix = int(
            (datetime.now(timezone.utc) - timedelta(hours=BRIEF_LOOKBACK_HOURS)).timestamp()
        )
        macro_query = (
            f"macro economic news interest rates inflation earnings GDP "
            f"sectors: {sectors_str}"
        )
        query_vec = await asyncio.to_thread(embed_text, macro_query)
        articles  = await asyncio.to_thread(
            search_news,
            query_vec,
            None,              # no ticker filter — macro
            exclude_tickers,   # exclude portfolio/watchlist tickers
            from_unix,
            15,
        )

        if not articles:
            return []

        headlines_text = "\n\n".join(
            f"[{a.get('source', 'Unknown')}] {a.get('headline', '')} — {a.get('summary_2sent', '')}"
            for a in articles
        )
        prompt = _SYSTEM.format(
            holdings_summary=holdings_summary,
            sectors=sectors_str,
            min_score=MACRO_RELEVANCE_MIN,
        )
        messages = [{"role": "user", "content": f"{prompt}\n\nHeadlines:\n{headlines_text}"}]

        response = await asyncio.to_thread(_llm.invoke, messages)
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        result = json.loads(raw.strip())
        return result if isinstance(result, list) else []
    except Exception:
        return []
