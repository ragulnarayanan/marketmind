"""
Agent 5 — Investment Verdict
Model: gpt-4o (highest-stakes reasoning)
Input: synthesis brief from Agent 4
"""
import asyncio
import json

from langchain_openai import ChatOpenAI

from config import GPT_SMART, OPENAI_API_KEY

_llm = ChatOpenAI(model=GPT_SMART, temperature=0.1, api_key=OPENAI_API_KEY)

_SYSTEM = """You are a seasoned investment advisor. Based on this research brief, \
give a structured investment verdict. Return JSON only, no markdown:
{{
  "verdict": "BUY|HOLD|SELL",
  "confidence": "HIGH|MEDIUM|LOW",
  "confidence_score": <int 1-10>,
  "reasoning": ["<point 1>", "<point 2>", "<point 3>"],
  "bull_case": "<str>",
  "bear_case": "<str>",
  "key_risks": ["<risk 1>", "<risk 2>", "<risk 3>"],
  "time_horizon": "SHORT|MEDIUM|LONG",
  "price_context": "<str>",
  "disclaimer": "Not financial advice. Do your own research."
}}
Be decisive. HOLD only for genuinely balanced risk/reward."""


async def run_verdict_agent(ticker: str, synthesis: dict) -> dict:
    try:
        brief_text = synthesis.get("unified_brief", "")
        positives  = synthesis.get("key_positives", [])
        negatives  = synthesis.get("key_negatives", [])

        user_content = (
            f"Stock: {ticker}\n\n"
            f"Research Brief:\n{brief_text}\n\n"
            f"Key Positives: {', '.join(positives)}\n"
            f"Key Negatives: {', '.join(negatives)}"
        )
        messages = [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user_content},
        ]

        response = await asyncio.to_thread(_llm.invoke, messages)
        raw = response.content.strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "verdict": "HOLD",
            "confidence": "LOW",
            "confidence_score": 1,
            "reasoning": ["Verdict generation failed — raw response returned."],
            "bull_case": "",
            "bear_case": "",
            "key_risks": [],
            "time_horizon": "MEDIUM",
            "price_context": "",
            "disclaimer": "Not financial advice. Do your own research.",
            "raw_response": response.content if "response" in dir() else "",
        }
    except Exception as e:
        return {
            "verdict": "HOLD",
            "confidence": "LOW",
            "confidence_score": 1,
            "reasoning": [f"Error: {e}"],
            "bull_case": "",
            "bear_case": "",
            "key_risks": [],
            "time_horizon": "MEDIUM",
            "price_context": "",
            "disclaimer": "Not financial advice. Do your own research.",
        }
