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

_PORTFOLIO_SUMMARY_SYSTEM = """You are a senior equity research analyst \
writing a morning portfolio brief for a private investor.

Write ONE paragraph of 5-7 sentences that reads like a well-crafted \
analyst morning note. It must:

1. Open with the portfolio's overall day — was it a good day, mixed, or bad?
2. Name the biggest movers specifically (ticker + % move + one-line reason why)
3. Connect individual stock moves to broader themes where relevant \
   (e.g. "NVDA's gain reflects the broader AI infrastructure bid")
4. Mention any tensions or contradictions across holdings
5. End with one sentence on what macro factor is most worth watching \
   for this specific portfolio today

Tone: confident, specific, analytical — like a Goldman morning note
NOT like a news summary or bullet list

STRICT: Only use facts from the articles and price data provided.
Do not use prior knowledge. If data is missing say so briefly and move on.

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
