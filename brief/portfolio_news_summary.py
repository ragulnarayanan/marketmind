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

Write FOUR paragraphs totalling 20-26 sentences. The voice is authoritative, \
direct, and specific — like a seasoned analyst hosting a financial podcast.

Paragraph 1 — Market & Portfolio Read (4-5 sentences):
Open with a punchy one-sentence market read for the day. Name every holding \
with company name + ticker + % change + the actual catalyst (earnings beat, analyst \
upgrade, product news, macro read-through). Identify the dominant theme tying the \
portfolio together. Use specific numbers wherever the data provides them.

Paragraph 2 — Stock-by-Stock Breakdown (8-10 sentences):
Go through each holding individually. For every stock: state what happened today, \
name the specific news catalyst driving the move, explain what it means for the \
company's near-term outlook, and flag any key risk or opportunity that the news surfaces. \
Do not group stocks together — each gets its own 1-2 sentence treatment. \
Reference specific article details, analyst quotes, earnings figures, or product \
announcements from the news provided.

Paragraph 3 — Cross-Portfolio Themes (4-5 sentences):
Identify 2-3 macro or sector forces that are simultaneously affecting multiple holdings. \
Call out reinforcing signals (two stocks benefiting from the same tailwind) and \
tensions (one macro force helping one holding while hurting another). \
Name the specific tickers and explain the mechanism, not just the theme.

Paragraph 4 — What to Watch (4-5 sentences):
Name the 3-4 key variables that matter most for this portfolio in the next 48-72 hours — \
earnings prints, Fed speakers, technical levels, macro data releases, product events. \
Be specific about dates and price levels where the data supports it. \
End with one clear, actionable takeaway sentence.

Style rules:
- Use company names alongside tickers on first mention: Apple (AAPL)
- Prefer active verbs: "cleared", "reversed", "absorbed", "reaccelerated", "flagged"
- Use specific numbers: price levels, % moves, consensus estimates, revenue figures
- No filler: never write "it is worth noting", "investors should be aware", \
  "in conclusion", "overall the portfolio", "it is important to"

STRICT: Only use facts from the data provided. If a data point is missing, skip it — \
do not fabricate prices, headlines, or estimates.

Return JSON only:
{
  "summary": "full brief here",
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
