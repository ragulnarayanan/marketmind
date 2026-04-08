"""
Agent 4 — Senior Equity Research Analyst (synthesis)
Model: gpt-4o-mini
Combines outputs from agents 1-3 into a unified research brief.
"""
import asyncio
import json

from langchain_openai import ChatOpenAI

from config import GPT_FAST, OPENAI_API_KEY

_llm = ChatOpenAI(model=GPT_FAST, temperature=0.2, api_key=OPENAI_API_KEY)

_SYSTEM = """You are a senior equity research analyst. Synthesize these three analyses \
of {ticker} into a coherent 300-word research brief. Write as a professional analyst — \
structured, factual, covering both positives and negatives. \
Cover: news & sentiment, SEC filing insights, financial position. \
Prose only, no bullet points. \
Return JSON only, no markdown: \
{{"unified_brief": "<str>", "key_positives": ["<str>"], "key_negatives": ["<str>"]}}"""


async def run_synthesis_agent(ticker: str, news: dict, sec: dict, financials: dict) -> dict:
    try:
        news_summary = (
            f"Sentiment: {news.get('sentiment_label', 'unknown')} "
            f"(score {news.get('sentiment_score', 'N/A')}/10). "
            f"{news.get('summary', '')} "
            f"Top headline: {news.get('top_headline', 'N/A')}. "
            f"Key risks: {', '.join(news.get('risks', []))}"
        )

        sec_summary = (
            f"Risk factors: {sec.get('risk_factors', {}).get('answer', 'N/A')} "
            f"Revenue outlook: {sec.get('revenue_outlook', {}).get('answer', 'N/A')} "
            f"Debt concerns: {sec.get('debt_concerns', {}).get('answer', 'N/A')} "
            f"Competition: {sec.get('competitive_threats', {}).get('answer', 'N/A')} "
            f"Capital allocation: {sec.get('capital_allocation', {}).get('answer', 'N/A')}"
        )

        fin_summary = (
            f"Valuation: {financials.get('valuation', 'N/A')} — {financials.get('valuation_reason', '')} "
            f"Health: {financials.get('financial_health', 'N/A')} — {financials.get('health_reason', '')} "
            f"Growth: {financials.get('growth_profile', 'N/A')} — {financials.get('growth_reason', '')} "
            f"Volume signal: {financials.get('volume_signal', 'N/A')} "
            f"Red flags: {', '.join(financials.get('red_flags', []))} "
            f"Green flags: {', '.join(financials.get('green_flags', []))}"
        )

        system = _SYSTEM.format(ticker=ticker)
        user_content = (
            f"=== NEWS & SENTIMENT ===\n{news_summary}\n\n"
            f"=== SEC FILING INSIGHTS ===\n{sec_summary}\n\n"
            f"=== FINANCIAL POSITION ===\n{fin_summary}"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]

        response = await asyncio.to_thread(_llm.invoke, messages)
        raw = response.content.strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "unified_brief": response.content if "response" in dir() else "Parse error",
            "key_positives": [],
            "key_negatives": [],
        }
    except Exception as e:
        return {"unified_brief": f"Synthesis unavailable: {e}", "key_positives": [], "key_negatives": []}
