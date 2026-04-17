"""
Agent 3 — Quantitative Analyst
Model: gemini-2.5-flash
Sources: yfinance (metrics, institutional holders, volume spikes)

All yfinance calls run sequentially in one thread to avoid Yahoo Finance
rate limiting (429s) that occur when multiple calls fire concurrently.
"""
import asyncio
import json
import time

import yfinance as yf
from langchain_google_genai import ChatGoogleGenerativeAI

from config import GEMINI_FAST, GOOGLE_API_KEY
from utils import parse_llm_json

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


def _fetch_all_yfinance(ticker: str) -> dict:
    """
    Fetch all required yfinance data sequentially using one Ticker object.
    Small sleeps between calls prevent Yahoo Finance 429 rate limits.
    """
    tk = yf.Ticker(ticker)

    # 1 — fundamentals + sector
    info = tk.info
    time.sleep(0.4)

    metrics = {
        "pe_ratio":       _safe(info.get("trailingPE") or info.get("forwardPE")),
        "pb_ratio":       _safe(info.get("priceToBook")),
        "ev_to_ebitda":   _safe(info.get("enterpriseToEbitda")),
        "profit_margins": _safe(info.get("profitMargins")),
        "debt_to_equity": _safe(info.get("debtToEquity")),
        "return_on_equity": _safe(info.get("returnOnEquity")),
        "beta":           _safe(info.get("beta")),
        "revenue_growth": _safe(info.get("revenueGrowth")),
        "free_cash_flow": _safe(info.get("freeCashflow"), 0),
        "market_cap":     _safe(info.get("marketCap"), 0),
        "company_name":   info.get("longName", ticker),
    }
    sector = info.get("sector", "Unknown")

    # 2 — volume history for spike detection
    spikes = []
    try:
        hist = tk.history(period="90d")
        time.sleep(0.4)
        if not hist.empty:
            hist = hist.copy()
            hist["avg_volume"] = hist["Volume"].rolling(window=20, min_periods=5).mean()
            hist["spike_ratio"] = hist["Volume"] / hist["avg_volume"]
            for date, row in hist[hist["spike_ratio"] >= 2.0].iterrows():
                spikes.append({
                    "date":        str(date.date()),
                    "spike_ratio": round(float(row["spike_ratio"]), 2),
                    "direction":   "buying pressure" if row["Close"] >= row["Open"]
                                   else "selling pressure",
                    "volume":      int(row["Volume"]),
                    "avg_volume":  int(row["avg_volume"]),
                })
    except Exception:
        pass

    # 3 — institutional holders
    inst_summary = "Institutional holder data unavailable"
    try:
        holders_df = tk.institutional_holders
        if holders_df is not None and not holders_df.empty:
            inst_summary = (
                f"Top holders: {', '.join(holders_df['Holder'].head(3).tolist())}"
            )
        else:
            inst_summary = "No institutional holder data"
    except Exception:
        pass

    return {"metrics": metrics, "sector": sector,
            "spikes": spikes, "inst_summary": inst_summary}


async def run_financials_agent(ticker: str) -> dict:
    try:
        data = await asyncio.to_thread(_fetch_all_yfinance, ticker)
        metrics      = data["metrics"]
        sector       = data["sector"]
        spikes       = data["spikes"]
        inst_summary = data["inst_summary"]

        spike_summary = (
            f"{len(spikes)} volume spike(s) in last 90 days. "
            + (
                f"Most recent: {spikes[-1]['date']} ({spikes[-1]['direction']}, "
                f"{spikes[-1]['spike_ratio']}x avg)"
                if spikes else "No recent spikes."
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
        raw    = response.content.strip()
        result = parse_llm_json(raw)
        result["raw_metrics"]   = metrics
        result["volume_spikes"] = spikes[:5]
        return result

    except json.JSONDecodeError:
        return {"error": "JSON parse failed", "raw_metrics": {}, "volume_spikes": []}
    except Exception as e:
        return {"error": str(e), "raw_metrics": {}, "volume_spikes": []}
