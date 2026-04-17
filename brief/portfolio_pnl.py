"""
Portfolio P&L computation — pure math, no LLM.
Uses bulk yfinance download for efficiency.
"""
import yfinance as yf


def compute_portfolio_snapshot(holdings: list[dict]) -> dict:
    """
    holdings: [{ ticker, qty, avg_cost }]
    Returns snapshot with per-holding metrics + totals.
    """
    if not holdings:
        return {"holdings": [], "total_market_value": 0.0, "total_pnl": 0.0, "total_pnl_pct": 0.0}

    tickers = [h["ticker"] for h in holdings]

    try:
        data = yf.download(tickers, period="2d", auto_adjust=True, progress=False)
    except Exception:
        return {"holdings": [], "error": "yfinance download failed",
                "total_market_value": 0.0, "total_pnl": 0.0, "total_pnl_pct": 0.0}

    # Handle single-ticker case (yfinance returns flat DataFrame)
    if len(tickers) == 1:
        close = data["Close"].rename(columns={data["Close"].columns[0]: tickers[0]}) \
            if hasattr(data["Close"], "columns") else data["Close"].to_frame(name=tickers[0])
    else:
        close = data["Close"]

    results = []
    for h in holdings:
        tk = h["ticker"]
        try:
            series = close[tk].dropna()
            curr = round(float(series.iloc[-1]), 2)
            prev = round(float(series.iloc[-2]) if len(series) >= 2 else curr, 2)
        except Exception:
            curr = prev = round(float(h["avg_cost"]), 2)

        daily_pct     = round((curr - prev) / prev * 100, 2) if prev else 0.0
        market_val    = round(curr * float(h["qty"]), 2)
        cost_basis    = round(float(h["avg_cost"]) * float(h["qty"]), 2)
        total_pnl     = round(market_val - cost_basis, 2)
        total_pnl_pct = round(total_pnl / cost_basis * 100, 2) if cost_basis else 0.0

        prev_market_val = round(prev * float(h["qty"]), 2)
        results.append({
            "ticker":           tk,
            "qty":              float(h["qty"]),
            "avg_cost":         round(float(h["avg_cost"]), 2),
            "current_price":    curr,
            "daily_pct":        daily_pct,
            "market_value":     market_val,
            "prev_market_value": prev_market_val,
            "total_pnl":        total_pnl,
            "total_pnl_pct":    total_pnl_pct,
        })

    total_market = sum(r["market_value"] for r in results)
    total_prev   = sum(r["prev_market_value"] for r in results)
    total_cost   = sum(r["qty"] * r["avg_cost"] for r in results)
    daily_pnl    = round(total_market - total_prev, 2)
    daily_pnl_pct = round(daily_pnl / total_prev * 100, 2) if total_prev else 0.0
    return {
        "holdings":           results,
        "total_market_value": round(total_market, 2),
        "daily_pnl":          daily_pnl,
        "daily_pnl_pct":      daily_pnl_pct,
        "total_pnl":          round(total_market - total_cost, 2),
        "total_pnl_pct":      round((total_market - total_cost) / total_cost * 100, 2)
                              if total_cost else 0.0,
    }
