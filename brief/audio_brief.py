"""
Audio brief generator — converts daily brief dict to spoken MP3 via OpenAI TTS.
"""
from datetime import datetime

from openai import OpenAI

from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

# Spoken name for common tickers — used in audio so TTS says "Apple" not "AAPL"
_SPOKEN_NAMES: dict[str, str] = {
    "AAPL":  "Apple",
    "MSFT":  "Microsoft",
    "NVDA":  "NVIDIA",
    "GOOGL": "Alphabet",
    "GOOG":  "Alphabet",
    "AMZN":  "Amazon",
    "META":  "Meta",
    "TSLA":  "Tesla",
    "AVGO":  "Broadcom",
    "TSM":   "Taiwan Semiconductor",
    "LLY":   "Eli Lilly",
    "V":     "Visa",
    "JPM":   "JPMorgan",
    "WMT":   "Walmart",
    "MA":    "Mastercard",
    "XOM":   "Exxon Mobil",
    "COST":  "Costco",
    "HD":    "Home Depot",
    "JNJ":   "Johnson and Johnson",
    "NFLX":  "Netflix",
    "PG":    "Procter and Gamble",
    "ORCL":  "Oracle",
    "BAC":   "Bank of America",
    "ABBV":  "AbbVie",
    "AMD":   "A M D",
    "CRM":   "Salesforce",
    "KO":    "Coca-Cola",
    "CVX":   "Chevron",
    "MRK":   "Merck",
    "PEP":   "PepsiCo",
    "ADBE":  "Adobe",
    "ACN":   "Accenture",
    "WFC":   "Wells Fargo",
    "UNH":   "UnitedHealth",
    "IBM":   "I B M",
    "QCOM":  "Qualcomm",
    "NOW":   "ServiceNow",
    "TXN":   "Texas Instruments",
    "PM":    "Philip Morris",
    "INTU":  "Intuit",
    "AMGN":  "Amgen",
    "CSCO":  "Cisco",
    "CAT":   "Caterpillar",
    "DIS":   "Disney",
    "GS":    "Goldman Sachs",
    "NEE":   "NextEra Energy",
    "ISRG":  "Intuitive Surgical",
    "BKNG":  "Booking Holdings",
    "AMAT":  "Applied Materials",
    "SPGI":  "S&P Global",
    "T":     "A T and T",
    "INTC":  "Intel",
    "MU":    "Micron",
    "UBER":  "Uber",
    "LYFT":  "Lyft",
    "SNAP":  "Snap",
    "SPOT":  "Spotify",
    "PYPL":  "PayPal",
    "SQ":    "Block",
    "SHOP":  "Shopify",
    "COIN":  "Coinbase",
    "PLTR":  "Palantir",
    "RIVN":  "Rivian",
    "F":     "Ford",
    "GM":    "General Motors",
    "BA":    "Boeing",
    "LMT":   "Lockheed Martin",
    "RTX":   "Raytheon",
    "UPS":   "U P S",
    "FDX":   "FedEx",
    "MCD":   "McDonald's",
    "SBUX":  "Starbucks",
    "NKE":   "Nike",
    "TGT":   "Target",
    "AMGN":  "Amgen",
    "PFE":   "Pfizer",
    "MRNA":  "Moderna",
    "BIIB":  "Biogen",
    "GILD":  "Gilead",
    "BMY":   "Bristol Myers Squibb",
    "CVS":   "C V S",
    "WBA":   "Walgreens",
}


def _spoken(ticker: str) -> str:
    """Return the natural spoken name for a ticker, falling back to the ticker itself."""
    return _SPOKEN_NAMES.get(ticker.upper(), ticker)


def write_audio_script(brief: dict) -> str:
    """
    Convert the daily brief dict into a natural spoken script.
    Reads like a professional financial podcast host.
    """
    now      = datetime.now()
    day_name = now.strftime("%A")
    date_str = now.strftime("%B %d")

    pnl      = brief.get("portfolio_snapshot", {})
    holdings = pnl.get("holdings", [])
    summary  = brief.get("portfolio_summary", {})
    macro    = brief.get("macro_alerts", [])
    signals  = brief.get("signals", {})

    total_val  = pnl.get("total_market_value", 0)
    total_pnl  = pnl.get("total_pnl", 0)
    total_pct  = pnl.get("total_pnl_pct", 0)
    # Compute daily P&L the same way the portfolio overview page does
    daily_pnl  = sum(h.get("market_value", 0) * h.get("daily_pct", 0) / 100 for h in holdings)
    daily_pct  = daily_pnl / total_val * 100 if total_val else 0.0

    direction = "up" if daily_pnl >= 0 else "down"
    pnl_word  = "gaining" if daily_pnl >= 0 else "losing"

    script = f"Welcome to your MarketMind brief for {day_name}, {date_str}.\n\n"

    # ── Portfolio overview ──────────────────────────────────────────────────
    script += (
        f"Your portfolio is {direction} {abs(daily_pct):.1f}% today, "
        f"{pnl_word} ${abs(daily_pnl):,.0f}. "
        f"Total portfolio value stands at ${total_val:,.0f}, "
        f"with an overall gain of {total_pct:+.1f}% from your cost basis.\n\n"
    )

    # ── Individual movers ───────────────────────────────────────────────────
    if holdings:
        sorted_h = sorted(holdings,
                          key=lambda x: abs(x.get("daily_pct", 0)),
                          reverse=True)
        script += "Looking at today's movers. "
        mover_parts = []
        for h in sorted_h:
            ticker = h.get("ticker", "")
            name   = _spoken(ticker)
            pct    = h.get("daily_pct", 0)
            move   = "up" if pct >= 0 else "down"
            signal = signals.get(ticker, {}).get("signal", "WAIT")
            mover_parts.append(
                f"{name} is {move} {abs(pct):.1f}%, "
                f"current signal is {signal.lower()}"
            )
        script += ". ".join(mover_parts) + ".\n\n"

    # ── Portfolio news summary ──────────────────────────────────────────────
    news_summary = summary.get("summary", "")
    if news_summary:
        # Truncate to ~1500 chars to stay under TTS 4096 limit (with room for other sections)
        if len(news_summary) > 1500:
            news_summary = news_summary[:1500].rsplit('. ', 1)[0] + '.'
        script += (
            f"Here is what is driving your portfolio today. "
            f"{news_summary}\n\n"
        )

    # ── Macro / world news ─────────────────────────────────────────────────
    if macro:
        script += "Now for the global headlines you should be aware of. "
        for m in macro[:3]:
            why    = m.get("why_matters", "")
            impact = m.get("impact", "neutral")
            if why:
                impact_word = (
                    "a positive development" if impact == "bullish"
                    else "a potential headwind" if impact == "bearish"
                    else "worth monitoring"
                )
                script += f"{why} This is {impact_word}. "
        script += "\n\n"

    # ── Closing ─────────────────────────────────────────────────────────────
    sentiment = summary.get("sentiment_label", "neutral")
    CLOSE = {
        "bullish": "Overall a positive picture for your book today. "
                   "Stay disciplined and have a great session.",
        "bearish": "Some caution is warranted today. "
                   "Keep an eye on your risk levels.",
        "mixed":   "A mixed picture today. Stay informed and trade carefully.",
        "neutral": "A steady day overall. "
                   "Keep watching the key levels.",
    }
    script += CLOSE.get(sentiment, CLOSE["neutral"])
    script += (
        " This has been your MarketMind daily brief.\n\n"
        "Quick heads up — everything you just heard is AI generated. "
        "MarketMind is not a registered investment advisor. "
        "Use the source articles to dig deeper, and always make your own call."
    )

    return script


def generate_audio_brief(brief: dict) -> bytes:
    """
    Generate MP3 audio from the daily brief using OpenAI TTS.
    Returns raw MP3 bytes.

    Voice options: alloy, echo, fable, onyx, nova, shimmer
    onyx = deep, professional male voice — best for financial content
    nova = warm, clear female voice — good alternative
    """
    script = write_audio_script(brief)

    response = client.audio.speech.create(
        model="tts-1",          # tts-1 = fast, tts-1-hd = higher quality
        voice="onyx",           # deep professional voice
        input=script,
        response_format="mp3",
        speed=0.95,             # slightly slower than default for clarity
    )

    return response.content     # raw MP3 bytes
