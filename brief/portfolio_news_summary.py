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

_PORTFOLIO_SUMMARY_SYSTEM = """You are the host of a sharp, no-fluff financial podcast in the style \
of Seeking Alpha's Wall Street Breakfast. Write a morning brief for a self-directed investor.

Write ONE tightly edited paragraph of 5-8 sentences. The voice is authoritative, \
direct, and specific — like a seasoned analyst who gets to the point fast.

Rules:
1. Open with a punchy one-sentence market read — not "markets were mixed", \
   but something like "It was a tale of two halves Tuesday, with AI names surging \
   while consumer discretionary faded on weak retail data."
2. Name every significant mover with ticker + % change + the actual catalyst driving it — \
   earnings beat, analyst upgrade, product news, macro read-through. Be specific.
3. Identify the dominant theme across the portfolio — e.g. "the common thread today \
   is the AI infrastructure buildout, which lifted both NVDA and MSFT while weighing \
   on legacy hardware names."
4. Call out any cross-holding tension — e.g. "AAPL's services strength is a bullish \
   data point for GOOG's ad business, but the iPhone demand question still hangs over both."
5. End with the ONE variable that matters most for this portfolio in the next 24-48 hours — \
   a Fed speaker, an earnings print, a technical level, a macro data release.

Style cues:
- Use company names alongside tickers on first mention (Apple (AAPL))
- Prefer active verbs: "cleared", "reversed", "absorbed", "reaccelerated"
- Use specific numbers: price levels, % moves, consensus estimates when available
- No filler phrases: never write "it is worth noting", "investors should be aware", \
  "in conclusion", "overall the portfolio"

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

        # News context — top 3 articles per ticker, most recent first
        news_context = ""
        for h in holdings:
            ticker   = h["ticker"]
            articles = news_by_ticker.get(ticker, [])[:3]
            if articles:
                news_context += f"\n\n{ticker} news:\n"
                for a in articles:
                    news_context += f"- {a.get('headline', '')} ({a.get('published_date', '')})\n"
                    content = a.get("full_text") or a.get("description", "")
                    if content:
                        news_context += f"  {content[:200]}\n"

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
