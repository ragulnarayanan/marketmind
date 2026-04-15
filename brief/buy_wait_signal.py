"""
Per-holding Buy / Wait / Sell signal for the daily brief.
Model: gpt-4o
"""
import asyncio
import json
import re

from langchain_openai import ChatOpenAI

from config import GPT_SMART, OPENAI_API_KEY

_llm = ChatOpenAI(model=GPT_SMART, temperature=0.1, api_key=OPENAI_API_KEY)


async def generate_signal(
    holding: dict,          # { ticker, qty, avg_cost, current_price, daily_pct, total_pnl_pct }
    news_summary: dict,     # result from summarize_stock_news_for_brief
    macro_context: list,    # list of macro alert dicts
) -> dict:
    ticker        = holding.get("ticker", "")
    current_price = holding.get("current_price", 0)
    avg_cost      = holding.get("avg_cost", 0)
    daily_pct     = holding.get("daily_pct", 0)
    total_pnl_pct = holding.get("total_pnl_pct", 0)

    # news_summary is a dict — extract text safely
    news_text = ""
    if isinstance(news_summary, dict):
        news_text      = news_summary.get("summary", "")
        news_sentiment = news_summary.get("sentiment_label", "neutral")
    elif isinstance(news_summary, str):
        news_text      = news_summary
        news_sentiment = "neutral"
    else:
        news_sentiment = "neutral"

    # macro_context is a list of dicts — convert to readable text
    macro_text = ""
    if macro_context:
        macro_items = []
        for m in macro_context[:3]:
            if isinstance(m, dict):
                macro_items.append(m.get("why_matters", m.get("headline", "")))
            elif isinstance(m, str):
                macro_items.append(m)
        macro_text = " | ".join(macro_items)

    prompt = f"""Stock: {ticker}
User average cost: ${avg_cost:.2f}
Current price: ${current_price:.2f} ({daily_pct:+.1f}% today, {total_pnl_pct:+.1f}% from cost basis)
News sentiment: {news_sentiment}
News summary: {news_text[:300] if news_text else 'No news available'}
Macro context: {macro_text[:200] if macro_text else 'No macro context'}

You are a sharp equity analyst on a financial podcast. Give a BUY / WAIT / SELL call on {ticker}.

Write a reason that sounds like a crisp analyst take — not a generic disclaimer. \
Two sentences max. Be direct: name the catalyst or risk, reference the price level if relevant, \
and tell the investor exactly what to watch. Examples of the right voice:
- "NVDA cleared key resistance at $900 on AI infrastructure demand; the risk/reward favors \
  adding here with $865 as your stop."
- "AAPL is digesting iPhone demand concerns — hold the position but don't add until \
  management clarifies China sell-through on the August call."
- "META has run 18% in three weeks with no new catalyst; trim into strength and \
  re-enter below $480 if the broader market pulls back."

Respond with JSON only, no markdown:
{{"signal": "BUY", "reason": "2-sentence analyst take here", "watch_price": null, "urgency": "MEDIUM"}}

signal must be exactly: BUY, WAIT, or SELL
urgency must be exactly: HIGH, MEDIUM, or LOW
watch_price is a float price level to watch, or null"""

    # Try up to 2 times
    for attempt in range(2):
        try:
            response = await asyncio.to_thread(
                _llm.invoke,
                [{"role": "user", "content": prompt}],
            )
            content = response.content.strip()
            if not content:
                continue
            content = re.sub(r"^```(?:json)?\s*\n?", "", content)
            content = re.sub(r"\n?```\s*$", "", content)
            result  = json.loads(content.strip())
            return {
                "ticker":      ticker,
                "signal":      result.get("signal", "WAIT").upper(),
                "reason":      result.get("reason", ""),
                "watch_price": result.get("watch_price"),
                "urgency":     result.get("urgency", "LOW").upper(),
            }
        except Exception:
            await asyncio.sleep(1)

    # Hardcoded fallback if both attempts fail
    return {
        "ticker":      ticker,
        "signal":      "WAIT",
        "reason":      "Could not generate signal — review news and financials manually.",
        "watch_price": None,
        "urgency":     "LOW",
    }
