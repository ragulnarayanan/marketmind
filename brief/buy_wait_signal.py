"""
Per-holding Buy / Wait / Sell signal for the daily brief.
Model: gpt-4o
"""
import asyncio
import json

from langchain_openai import ChatOpenAI

from config import GPT_SMART, OPENAI_API_KEY

_llm = ChatOpenAI(model=GPT_SMART, temperature=0.1, api_key=OPENAI_API_KEY)

_PROMPT = """Stock: {ticker}
User avg cost: ${avg_cost} | Current: ${current_price}
Daily change: {daily_pct}% | From cost basis: {total_pnl_pct}%
News today: {news_summary}
Macro context: {macro_summary}

Should the user BUY more, WAIT, or SELL?
Return JSON only, no markdown:
{{"signal": "BUY|WAIT|SELL", "reason": "<2 sentences max>",
  "watch_price": <float or null>, "urgency": "HIGH|MEDIUM|LOW"}}"""


async def generate_signal(
    holding: dict,
    news: dict,
    macro_alerts: list[dict],
) -> dict:
    ticker = holding["ticker"]
    try:
        macro_summary = (
            "; ".join(
                f"{m.get('headline', '')} ({m.get('impact_direction', 'neutral')})"
                for m in (macro_alerts or [])[:3]
            )
            or "No significant macro news today."
        )
        prompt = _PROMPT.format(
            ticker=ticker,
            avg_cost=round(float(holding.get("avg_cost", 0)), 2),
            current_price=round(float(holding.get("current_price", 0)), 2),
            daily_pct=round(float(holding.get("daily_pct", 0)), 2),
            total_pnl_pct=round(float(holding.get("total_pnl_pct", 0)), 2),
            news_summary=news.get("summary", "No news available."),
            macro_summary=macro_summary,
        )
        messages = [{"role": "user", "content": prompt}]
        try:
            response = await asyncio.to_thread(_llm.invoke, messages)
            raw = response.content.strip()
            if not raw:
                raise ValueError("Empty response")
            result = json.loads(raw)
            result["ticker"] = ticker
            return result
        except Exception:
            # Retry with minimal prompt
            try:
                current_price = round(float(holding.get("current_price", 0)), 2)
                avg_cost      = round(float(holding.get("avg_cost", 0)), 2)
                retry_prompt  = (
                    f'For stock {ticker} current price ${current_price} vs avg cost '
                    f'${avg_cost}, respond with JSON only: '
                    f'{{"signal": "WAIT", "reason": "Insufficient data", '
                    f'"watch_price": null, "urgency": "LOW"}}'
                )
                response = await asyncio.to_thread(
                    _llm.invoke, [{"role": "user", "content": retry_prompt}]
                )
                raw = response.content.strip()
                result = json.loads(raw)
                result["ticker"] = ticker
                return result
            except Exception:
                return {
                    "ticker":      ticker,
                    "signal":      "WAIT",
                    "reason":      "Signal generation unavailable — check back later.",
                    "watch_price": None,
                    "urgency":     "LOW",
                }
    except Exception as e:
        return {
            "ticker":      ticker,
            "signal":      "WAIT",
            "reason":      f"Signal generation failed: {e}",
            "watch_price": None,
            "urgency":     "LOW",
        }
