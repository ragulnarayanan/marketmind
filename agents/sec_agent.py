"""
Agent 2 — SEC Filing Analyst
Model: gemini-1.5-pro (1M context, ideal for long filings)
Sources: Qdrant RAG over pre-embedded SEC chunks
"""
import asyncio
import json

from langchain_google_genai import ChatGoogleGenerativeAI

from config import GEMINI_PRO, GOOGLE_API_KEY, TOP_K_VECTOR_RESULTS
from data.qdrant_client import search_sec_chunks
from utils.embeddings import embed_text

_llm = ChatGoogleGenerativeAI(
    model=GEMINI_PRO, temperature=0.1, google_api_key=GOOGLE_API_KEY
)

_QUESTIONS = [
    "What are the primary risk factors?",
    "What does management say about revenue growth and outlook?",
    "Are there going-concern warnings or significant debt issues?",
    "What are the main competitive threats mentioned?",
    "What are the capital allocation priorities?",
]

_SYSTEM = (
    "You are an SEC filing analyst. Using ONLY these excerpts from {ticker}'s {filing_type}, "
    "answer in 2-3 sentences. If excerpts are insufficient, say so. "
    'Return JSON only: {{"answer": "<str>", "confidence": "high|medium|low"}}'
)


async def _ask_one(ticker: str, filing_type: str, question: str) -> dict:
    query_vec = await asyncio.to_thread(embed_text, question)
    chunks = await asyncio.to_thread(
        search_sec_chunks, query_vec, ticker, filing_type, TOP_K_VECTOR_RESULTS
    )

    if not chunks:
        return {"answer": "No relevant filing excerpts found.", "confidence": "low"}

    excerpts = "\n\n---\n\n".join(c.get("text", "") for c in chunks)
    system = _SYSTEM.format(ticker=ticker, filing_type=filing_type)
    messages = [
        {"role": "user", "content": f"{system}\n\nExcerpts:\n{excerpts}\n\nQuestion: {question}"},
    ]
    try:
        response = await asyncio.to_thread(_llm.invoke, messages)
        raw = response.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception:
        return {"answer": response.content if "response" in dir() else "Parse error", "confidence": "low"}


async def run_sec_agent(ticker: str, filing_type: str = "10-K") -> dict:
    try:
        tasks = [_ask_one(ticker, filing_type, q) for q in _QUESTIONS]
        answers = await asyncio.gather(*tasks)
        return {
            "filing_type": filing_type,
            "risk_factors": answers[0],
            "revenue_outlook": answers[1],
            "debt_concerns": answers[2],
            "competitive_threats": answers[3],
            "capital_allocation": answers[4],
        }
    except Exception as e:
        return {
            "filing_type": filing_type,
            "error": str(e),
            "risk_factors": {"answer": "Unavailable", "confidence": "low"},
            "revenue_outlook": {"answer": "Unavailable", "confidence": "low"},
            "debt_concerns": {"answer": "Unavailable", "confidence": "low"},
            "competitive_threats": {"answer": "Unavailable", "confidence": "low"},
            "capital_allocation": {"answer": "Unavailable", "confidence": "low"},
        }
