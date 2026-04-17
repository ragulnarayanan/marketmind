"""
Portfolio-level news summary — one unified analyst-style paragraph
covering all holdings. Model: gpt-4o.
"""
import asyncio
from datetime import datetime

from langchain_openai import ChatOpenAI

from config import GPT_SMART, OPENAI_API_KEY
from utils import parse_llm_json

_llm = ChatOpenAI(model=GPT_SMART, temperature=0.2, api_key=OPENAI_API_KEY)

_PORTFOLIO_SUMMARY_SYSTEM = """You are the host of a sharp, no-fluff financial podcast. \
Write a morning brief for a self-directed investor.

Write THREE focused paragraphs totalling 12-16 sentences. The voice is authoritative, \
direct, and specific — like a seasoned analyst hosting a financial podcast.

Paragraph 1 — Market & Portfolio Read (4-5 sentences):
Open with a punchy one-sentence market read for the day. Name every significant mover \
with company name + ticker + % change + the actual catalyst (earnings beat, analyst \
upgrade, product news, macro read-through). Identify the dominant theme tying the \
portfolio together. Use specific numbers wherever the data provides them.

Paragraph 2 — Deep Dive (5-6 sentences):
Pick the 2-3 most important stories from the news and go deeper. What exactly happened, \
what does it mean for the specific holding, and how does it connect to the broader \
sector or macro picture? Call out cross-holding tensions or reinforcing signals — \
e.g. the same AI spend that lifts one holding pressures another. Reference specific \
article details from the news provided.

Paragraph 3 — What to Watch (3-4 sentences):
Name the 2-3 key variables that matter most for this portfolio in the next 48-72 hours — \
a Fed speaker, an earnings print, a technical level, a macro data release, a product \
event. Be specific about dates and price levels where possible. End with one clear \
takeaway sentence the investor can act on.

Style rules:
- Use company names alongside tickers on first mention: Apple (AAPL)
- Prefer active verbs: "cleared", "reversed", "absorbed", "reaccelerated", "flagged"
- Use specific numbers: price levels, % moves, consensus estimates
- No filler: never write "it is worth noting", "investors should be aware", \
  "in conclusion", "overall the portfolio", "it is important to"

STRICT: Only use facts from the data provided. If a data point is missing, skip it — \
do not fabricate prices, headlines, or estimates.

Return JSON only:
{
  "summary": "full paragraph here",
  "sentiment_label": "bullish|bearish|mixed",
  "sentiment_score": float 0-10
}"""


async def generate_portfolio_summary(
    holdings: list[dict],       # [{ticker, qty, avg_cost, current_price, daily_pct, total_pnl_pct}]
    news_by_ticker: dict,       # {ticker: [article payloads from Qdrant]}
) -> dict:
    """
    Generate one unified analyst-style paragraph covering all holdings together.
    """
    try:
        # Portfolio context — sorted by biggest mover first
        portfolio_context = "\n".join([
            f"{h['ticker']}: ${h.get('current_price', 0):.2f} "
            f"({h.get('daily_pct', 0):+.1f}% today, "
            f"{h.get('total_pnl_pct', 0):+.1f}% from cost)"
            for h in sorted(holdings, key=lambda x: abs(x.get("daily_pct", 0)), reverse=True)
        ])

        # News context — top 5 articles per ticker, most recent first
        # Prefer full scraped text; fall back to description
        news_context = ""
        for h in holdings:
            ticker   = h["ticker"]
            articles = news_by_ticker.get(ticker, [])[:5]
            if articles:
                news_context += f"\n\n{ticker} news:\n"
                for a in articles:
                    news_context += f"- {a.get('headline', '')} ({a.get('published_date', '')})\n"
                    content = a.get("full_text") or a.get("description", "")
                    if content:
                        news_context += f"  {content[:1500]}\n"

        user_message = (
            f"Portfolio positions:\n{portfolio_context}"
            f"\n\nRecent news:{news_context}"
            f"\n\nWrite the portfolio morning brief paragraph."
        )

        messages = [
            {"role": "system", "content": _PORTFOLIO_SUMMARY_SYSTEM},
            {"role": "user",   "content": user_message},
        ]

        response = await asyncio.to_thread(_llm.invoke, messages)
        result   = parse_llm_json(response.content.strip())

        return {
            "summary":         result.get("summary", ""),
            "sentiment_label": result.get("sentiment_label", "neutral"),
            "sentiment_score": float(result.get("sentiment_score", 5.0)),
            "tickers_covered": [h["ticker"] for h in holdings],
            "generated_at":    datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "summary":         f"Portfolio summary unavailable: {e}",
            "sentiment_label": "neutral",
            "sentiment_score": 5.0,
            "tickers_covered": [h["ticker"] for h in holdings],
            "generated_at":    datetime.utcnow().isoformat(),
        }
