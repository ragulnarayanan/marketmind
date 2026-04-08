import yfinance as yf
import pandas as pd
from config import SPIKE_THRESHOLD


def detect_volume_spikes(
    ticker: str,
    lookback_days: int = 90,
    threshold: float = SPIKE_THRESHOLD,
) -> list[dict]:
    """
    Detect abnormal volume spikes for a ticker over the lookback window.

    Returns a list of dicts: { date, spike_ratio, direction, volume, avg_volume }
    """
    try:
        hist = yf.Ticker(ticker).history(period=f"{lookback_days}d")
        if hist.empty:
            return []

        hist = hist.copy()
        hist["avg_volume"] = hist["Volume"].rolling(window=20, min_periods=5).mean()
        hist["spike_ratio"] = hist["Volume"] / hist["avg_volume"]

        spikes = hist[hist["spike_ratio"] >= threshold].copy()
        result = []
        for date, row in spikes.iterrows():
            direction = "buying pressure" if row["Close"] >= row["Open"] else "selling pressure"
            result.append(
                {
                    "date": str(date.date()),
                    "spike_ratio": round(float(row["spike_ratio"]), 2),
                    "direction": direction,
                    "volume": int(row["Volume"]),
                    "avg_volume": int(row["avg_volume"]),
                }
            )
        return result
    except Exception:
        return []
