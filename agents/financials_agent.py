"""
Agent 3 — Quantitative Analyst
Model: gemini-1.5-flash
Sources: yfinance (metrics, institutional holders, insider tx) + volume spike detection
"""
import asyncio
import json

import yfinance as yf
from langchain_google_genai import ChatGoogleGenerativeAI

from config import GEMINI_FAST, GOOGLE_API_KEY
from utils.sector_mapper import get_sector
from utils.volume_analyzer import detect_volume_spikes

_llm = ChatGoogleGenerativeAI(
    model=GEMINI_FAST, temperature=0.1, google_api_key=GOOGLE_API_KEY
)

_SYSTEM = """You are a quantitative analyst. Analyze these financial metrics for \
{ticker} in the {sector} sector. Return JSON only, no markdown:
{{
  "valuation": "undervalued|fairly_valued|overvalued",
  "valuation_reason": "<str>",
  "financial_health": "strong|moderate|weak",
  "health_reason": "<str>",
  "growth_profile": "high_growth|stable|declining",
  "growth_reason": "<str>",
  "volume_signal": "<str>",
  "institutional_signal": "<str>",
  "key_metrics": {{
    "pe": <float or null>,
    "pb": <float or null>,
    "ev_ebitda": <float or null>,
    "margin": <float or null>,
    "de_ratio": <float or null>,
    "roe": <float or null>,
    "beta": <float or null>
  }},
  "red_flags": ["<str>"],
  "green_flags": ["<str>"]
}}"""


def _safe(val, decimals=2):
    try:
        return round(float(val), decimals) if val is not None else None
    except Exception:
        return None


async def _fetch_metrics(ticker: str) -> dict:
    info = await asyncio.to_thread(lambda: yf.Ticker(ticker).info)
    return {
        "pe_ratio": _safe(info.get("trailingPE") or info.get("forwardPE")),
        "pb_ratio": _safe(info.get("priceToBook")),
        "ev_to_ebitda": _safe(info.get("enterpriseToEbitda")),
        "profit_margins": _safe(info.get("profitMargins")),
        "debt_to_equity": _safe(info.get("debtToEquity")),
        "return_on_equity": _safe(info.get("returnOnEquity")),
        "beta": _safe(info.get("beta")),
        "revenue_growth": _safe(info.get("revenueGrowth")),
        "free_cash_flow": _safe(info.get("freeCashflow"), 0),
        "market_cap": _safe(info.get("marketCap"), 0),
        "company_name": info.get("longName", ticker),
    }


async def run_financials_agent(ticker: str) -> dict:
    try:
        metrics, sector = await asyncio.gather(
            _fetch_metrics(ticker),
            asyncio.to_thread(get_sector, ticker),
        )
        spikes = await asyncio.to_thread(detect_volume_spikes, ticker, 90, 2.0)

        # Institutional holders summary
        try:
            holders_df = await asyncio.to_thread(
                lambda: yf.Ticker(ticker).institutional_holders
            )
            inst_summary = (
                f"Top holders: {', '.join(holders_df['Holder'].head(3).tolist())}"
                if holders_df is not None and not holders_df.empty
                else "No institutional holder data"
            )
        except Exception:
            inst_summary = "Institutional holder data unavailable"

        spike_summary = (
            f"{len(spikes)} volume spike(s) in last 90 days. "
            + (
                f"Most recent: {spikes[-1]['date']} ({spikes[-1]['direction']}, "
                f"{spikes[-1]['spike_ratio']}x avg)"
                if spikes
                else "No recent spikes."
            )
        )

        metrics_text = (
            f"P/E: {metrics['pe_ratio']}, P/B: {metrics['pb_ratio']}, "
            f"EV/EBITDA: {metrics['ev_to_ebitda']}, "
            f"Profit Margin: {metrics['profit_margins']}, "
            f"D/E: {metrics['debt_to_equity']}, ROE: {metrics['return_on_equity']}, "
            f"Beta: {metrics['beta']}, Revenue Growth: {metrics['revenue_growth']}, "
            f"FCF: {metrics['free_cash_flow']}"
        )

        system = _SYSTEM.format(ticker=ticker, sector=sector)
        user_content = (
            f"Metrics for {ticker}:\n{metrics_text}\n\n"
            f"Volume analysis: {spike_summary}\n\n"
            f"Institutional holders: {inst_summary}"
        )
        messages = [{"role": "user", "content": f"{system}\n\n{user_content}"}]

        response = await asyncio.to_thread(_llm.invoke, messages)
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        result = json.loads(raw.strip())
        result["raw_metrics"] = metrics
        result["volume_spikes"] = spikes[:5]
        return result
    except json.JSONDecodeError:
        return {"raw_response": raw if "raw" in dir() else "", "error": "JSON parse failed",
                "raw_metrics": {}, "volume_spikes": []}
    except Exception as e:
        return {"error": str(e), "raw_metrics": {}, "volume_spikes": []}
