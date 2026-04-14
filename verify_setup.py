"""
Run this before any other development to verify all service connections.
    python verify_setup.py
"""
import os
from dotenv import load_dotenv
os.environ["GRPC_VERBOSITY"] = "ERROR"

load_dotenv()

print("\n=== MarketMind Setup Verification ===\n")

# ── Firestore ──────────────────────────────────────────────────────────────────
try:
    from config import db
    db.collection("verify").document("test").set({"ok": True})
    db.collection("verify").document("test").delete()
    print("OK  Firestore — connected (us-east1)")
except Exception as e:
    print(f"FAIL Firestore: {e}")

# ── Qdrant ─────────────────────────────────────────────────────────────────────
try:
    from qdrant_client import QdrantClient
    q = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY") or None)
    collections = q.get_collections().collections
    print(f"OK  Qdrant — {len(collections)} collection(s)")
    if not collections:
        print("    Note: Run data.qdrant_client.init_collections() to create collections.")
except Exception as e:
    print(f"FAIL Qdrant: {e}")
    print("     Fix: check QDRANT_URL and QDRANT_API_KEY in .env")

# ── OpenAI ─────────────────────────────────────────────────────────────────────
try:
    import openai
    openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY")).models.list()
    print("OK  OpenAI")
except Exception as e:
    print(f"FAIL OpenAI: {e}")

# ── Google Gemini ──────────────────────────────────────────────────────────────
try:
    from google import genai
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    print("OK  Google Gemini")
except Exception as e:
    print(f"FAIL Google Gemini: {e}")

# ── yfinance ───────────────────────────────────────────────────────────────────
try:
    import yfinance as yf
    ticker = yf.Ticker("AAPL")
    hist = ticker.history(period="5d")
    if hist.empty:
        raise ValueError("yfinance returned no data")
    price = hist["Close"].iloc[-1]
    print(f"OK  yfinance — AAPL: ${round(price, 2)}")
except Exception as e:
    print(f"FAIL yfinance: {e}")

# ── NewsAPI ────────────────────────────────────────────────────────────────────
try:
    from newsapi import NewsApiClient
    na = NewsApiClient(api_key=os.getenv("NEWSAPI_KEY", ""))
    na.get_sources(language="en")
    print("OK  NewsAPI")
except Exception as e:
    print(f"FAIL NewsAPI: {e}")

# ── Finnhub ────────────────────────────────────────────────────────────────────
try:
    import finnhub
    fh = finnhub.Client(api_key=os.getenv("FINNHUB_API_KEY", ""))
    fh.company_profile2(symbol="AAPL")
    print("OK  Finnhub")
except Exception as e:
    print(f"FAIL Finnhub: {e}")

print("\n=== Done ===\n")

# ── Qdrant ─────────────────────────────────────────────────────────────────────
try:
    from data.qdrant_client import init_collections
    init_collections()
    print("OK  Qdrant collections initialised")
except Exception as e:
    print("FAIL Qdrant init:", e)
