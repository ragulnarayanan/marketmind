"""
Reusable UI component helpers for MarketMind.
All color values follow the design system — no hardcoded colors in page files.
"""


def green_badge(text: str) -> str:
    return (
        f"<span style='background:rgba(34,197,94,0.1);"
        f"color:#22c55e;border:1px solid rgba(34,197,94,0.3);"
        f"padding:3px 10px;border-radius:20px;"
        f"font-size:12px;font-weight:600;font-family:Inter,sans-serif'>"
        f"{text}</span>"
    )


def red_badge(text: str) -> str:
    return (
        f"<span style='background:rgba(239,68,68,0.1);"
        f"color:#ef4444;border:1px solid rgba(239,68,68,0.3);"
        f"padding:3px 10px;border-radius:20px;"
        f"font-size:12px;font-weight:600;font-family:Inter,sans-serif'>"
        f"{text}</span>"
    )


def neutral_badge(text: str) -> str:
    return (
        f"<span style='background:#111111;"
        f"color:#a1a1aa;border:1px solid #1a1a1a;"
        f"padding:3px 10px;border-radius:20px;"
        f"font-size:12px;font-weight:600;font-family:Inter,sans-serif'>"
        f"{text}</span>"
    )


def signal_badge(signal: str) -> str:
    signal = signal.upper()
    if signal == "BUY":
        return green_badge("BUY")
    elif signal == "SELL":
        return red_badge("SELL")
    return neutral_badge("WAIT")


def sentiment_badge(label: str) -> str:
    label = label.lower()
    if label == "bullish":
        return green_badge("Bullish")
    elif label == "bearish":
        return red_badge("Bearish")
    elif label == "mixed":
        return neutral_badge("Mixed")
    return neutral_badge("Neutral")


def pct_colored(pct: float) -> str:
    """Return colored percentage string HTML."""
    if pct > 0:
        return (
            f"<span style='color:#22c55e;font-weight:600;"
            f"font-family:Inter,sans-serif'>+{pct:.2f}%</span>"
        )
    elif pct < 0:
        return (
            f"<span style='color:#ef4444;font-weight:600;"
            f"font-family:Inter,sans-serif'>{pct:.2f}%</span>"
        )
    return (
        f"<span style='color:#a1a1aa;font-weight:500;"
        f"font-family:Inter,sans-serif'>0.00%</span>"
    )


def dollar_colored(val: float) -> str:
    """Return colored dollar value string HTML."""
    if val > 0:
        return (
            f"<span style='color:#22c55e;font-weight:600;"
            f"font-family:Inter,sans-serif'>+${val:,.2f}</span>"
        )
    elif val < 0:
        return (
            f"<span style='color:#ef4444;font-weight:600;"
            f"font-family:Inter,sans-serif'>-${abs(val):,.2f}</span>"
        )
    return (
        f"<span style='color:#a1a1aa;font-weight:500;"
        f"font-family:Inter,sans-serif'>$0.00</span>"
    )


def section_header(title: str, subtitle: str = "") -> str:
    sub = (
        f"<p style='color:#52525b;font-size:13px;"
        f"margin:4px 0 0;font-family:Inter,sans-serif'>{subtitle}</p>"
        if subtitle else ""
    )
    return (
        f"<div style='margin:28px 0 16px'>"
        f"<h2 style='color:#ffffff;font-size:18px;font-weight:600;"
        f"letter-spacing:-0.01em;margin:0;font-family:Inter,sans-serif;"
        f"border-bottom:1px solid #1a1a1a;padding-bottom:10px'>{title}</h2>"
        f"{sub}</div>"
    )


def news_card(headline: str, summary: str, source: str,
              date: str, url: str = "") -> str:
    link = (
        f"<a href='{url}' style='color:#22c55e;font-size:12px;"
        f"text-decoration:none;font-weight:500'>Read more →</a>"
        if url else ""
    )
    return (
        f"<div style='background:#0a0a0a;border:1px solid #1a1a1a;"
        f"border-radius:10px;padding:16px 20px;margin-bottom:10px;"
        f"transition:border-color 0.2s ease' "
        f"onmouseover=\"this.style.borderColor='#22c55e'\" "
        f"onmouseout=\"this.style.borderColor='#1a1a1a'\">"
        f"<p style='color:#ffffff;font-size:14px;font-weight:600;"
        f"margin:0 0 6px;font-family:Inter,sans-serif'>{headline}</p>"
        f"<p style='color:#a1a1aa;font-size:13px;line-height:1.6;"
        f"margin:0 0 10px;font-family:Inter,sans-serif'>{summary}</p>"
        f"<div style='display:flex;justify-content:space-between;"
        f"align-items:center'>"
        f"<span style='color:#52525b;font-size:11px;"
        f"font-family:Inter,sans-serif'>{source} · {date}</span>"
        f"{link}</div></div>"
    )


def macro_card(headline: str, why_matters: str, impact: str,
               score: int, source: str, url: str = "") -> str:
    impact_color = (
        "#22c55e" if impact == "bullish"
        else "#ef4444" if impact == "bearish"
        else "#a1a1aa"
    )
    link = (
        f"<a href='{url}' style='color:#22c55e;font-size:12px;"
        f"text-decoration:none;font-weight:500'>Read →</a>"
        if url else ""
    )
    return (
        f"<div style='background:#0a0a0a;border:1px solid #1a1a1a;"
        f"border-left:3px solid {impact_color};"
        f"border-radius:10px;padding:14px 18px;margin-bottom:8px'>"
        f"<div style='display:flex;justify-content:space-between;"
        f"align-items:flex-start;gap:12px'>"
        f"<div style='flex:1'>"
        f"<p style='color:#ffffff;font-size:13px;font-weight:600;"
        f"margin:0 0 4px;font-family:Inter,sans-serif'>{headline}</p>"
        f"<p style='color:{impact_color};font-size:12px;"
        f"margin:0;font-family:Inter,sans-serif'>{why_matters}</p>"
        f"</div>"
        f"<div style='text-align:right;flex-shrink:0'>"
        f"<span style='color:#52525b;font-size:11px;"
        f"display:block;font-family:Inter,sans-serif'>"
        f"Relevance {score}/10</span>"
        f"{link}</div></div></div>"
    )
