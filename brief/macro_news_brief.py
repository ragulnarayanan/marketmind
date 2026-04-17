"""
Macro news alerts scored for portfolio relevance.
Sources: RSS feeds + Finnhub general news.
Model: gpt-4o-mini (fast, handles long headline lists well).
"""
import asyncio
import json
import re
from datetime import datetime, timezone

import feedparser
from langchain_openai import ChatOpenAI

from config import GPT_FAST, OPENAI_API_KEY

_llm = ChatOpenAI(model=GPT_FAST, temperature=0, api_key=OPENAI_API_KEY)

RSS_FEEDS = {
    "Reuters World":    "https://feeds.reuters.com/reuters/worldnews",
    "Reuters Business": "https://feeds.reuters.com/reuters/businessnews",
    "BBC World":        "http://feeds.bbci.co.uk/news/world/rss.xml",
    "WSJ Markets":      "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "Oil Price":        "https://oilprice.com/rss/main",
    "FT Markets":       "https://www.ft.com/markets?format=rss",
}


def _fetch_rss_articles() -> list[dict]:
    """Fetch latest articles from all RSS feeds. Never raises — skips failed feeds."""
    articles = []
    for source_name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
                headline = entry.get("title", "").strip()
                if not headline:
                    continue
                articles.append({
                    "headline":     headline,
                    "description":  entry.get("summary", "")[:300],
                    "url":          entry.get("link", ""),
                    "source_name":  source_name,
                    "published_at": entry.get("published", ""),
                    "has_url":      True,
                    "source_type":  "rss",
                })
        except Exception:
            continue
    return articles


def _fetch_finnhub_general_news() -> list[dict]:
    """Fetch general market news from Finnhub. Finnhub URLs are not usable."""
    articles = []
    try:
        fc   = finnhub.Client(api_key=FINNHUB_API_KEY)
        news = fc.general_news("general", min_id=0)
        for a in (news or [])[:20]:
            headline = (a.get("headline") or "").strip()
            if not headline:
                continue
            articles.append({
                "headline":     headline,
                "description":  a.get("summary", "")[:300],
                "url":          None,
                "source_name":  a.get("source", "Finnhub"),
                "published_at": datetime.fromtimestamp(
                                    a.get("datetime", 0), tz=timezone.utc
                                ).strftime("%Y-%m-%d"),
                "has_url":      False,
                "source_type":  "finnhub",
            })
    except Exception:
        pass
    return articles


def _get_sectors(holdings: list[dict]) -> dict:
    from utils.sector_mapper import get_sector
    return {h["ticker"]: get_sector(h["ticker"]) for h in holdings}


async def get_macro_alerts_for_portfolio(
    holdings: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """
    Fetch world/macro news from RSS + Finnhub.
    Score each article 0-10 for portfolio relevance using GPT-4o-mini.
    Return top_n items scoring 6+.
    """
    if not holdings:
        return []

    # RSS feeds only — all articles have valid URLs for the "Read →" link.
    # Finnhub general news has no URLs so it was excluded from Global Headlines.
    all_articles = await asyncio.to_thread(_fetch_rss_articles)

    if not all_articles:
        return []

    # Build portfolio context
    sectors     = await asyncio.to_thread(_get_sectors, holdings)
    holdings_str = "\n".join(
        f"  {h['ticker']} ({sectors.get(h['ticker'], 'unknown sector')})"
        for h in holdings
    )

    # Format top-40 headlines for the prompt
    headlines_text = "\n".join(
        f"{i + 1}. [{a['source_name']}] {a['headline']}"
        for i, a in enumerate(all_articles[:40])
    )

    prompt = f"""The investor holds these stocks:
{holdings_str}

You are a macro analyst on a financial podcast. Review these headlines and score each \
0-10 for relevance to this specific portfolio. Only return items scoring 6 or above.

For each relevant headline write a "why_matters" in ONE punchy sentence. \
Name the specific ticker(s) affected, the direction of impact, and the mechanism — \
not just "this could affect tech stocks." Make it sound like a sharp analyst insight.

Good examples:
- "A Fed rate-cut delay is the key headwind for NVDA and META — higher-for-longer reprices \
  their growth multiples, and the market hasn't fully absorbed that yet."
- "Rising oil prices are a direct margin headwind for Delta (DAL) and a tailwind for \
  energy holdings; watch the $90/bbl level as the inflection point."
- "China's stimulus miss removes a near-term catalyst for Apple (AAPL), which needs \
  Greater China revenue recovery to hit the Street's FY25 numbers."

Headlines:
{headlines_text}

Return JSON array only, no markdown:
[
  {{
    "index": int,
    "headline": "headline text",
    "source": "source name",
    "relevance_score": int,
    "why_matters": "one punchy analyst sentence naming specific ticker and mechanism",
    "impact": "bullish|bearish|neutral"
  }}
]
If nothing scores 6+, return []"""

    try:
        response = await asyncio.to_thread(
            _llm.invoke,
            [{"role": "user", "content": prompt}],
        )
        content = response.content.strip()
        content = re.sub(r"^```(?:json)?\s*\n?", "", content)
        content = re.sub(r"\n?```\s*$", "", content)
        scored  = json.loads(content.strip())

        if not isinstance(scored, list):
            return []

        # Attach URL and published_at from original articles
        output = []
        for item in scored:
            idx = item.get("index", 1) - 1
            if 0 <= idx < len(all_articles):
                original = all_articles[idx]
                output.append({
                    "headline":        item.get("headline",        original["headline"]),
                    "source_name":     item.get("source",          original["source_name"]),
                    "url":             original.get("url"),
                    "has_url":         original.get("has_url", False),
                    "relevance_score": item.get("relevance_score", 0),
                    "why_matters":     item.get("why_matters", ""),
                    "impact":          item.get("impact", "neutral"),
                    "published_at":    original.get("published_at", ""),
                })

        return sorted(output, key=lambda x: x["relevance_score"], reverse=True)[:top_n]

    except Exception as e:
        return []
