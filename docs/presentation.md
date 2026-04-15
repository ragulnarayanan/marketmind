# MarketMind — Presentation Slides

---

## Slide 1 — Title

**MarketMind**
*AI-Powered Portfolio Intelligence for the Everyday Investor*

> "A daily briefing for retail investors who don't have time to be their own analyst —
> delivered in the voice of a financial podcast, in under 2 minutes."

- Built with: Python · Streamlit · GPT-4o · Gemini 2.5 Flash · Qdrant · GCP
- GitHub: github.com/ragulnarayanan/marketmind

---

## Slide 2 — The Problem

**Retail investors are outgunned.**

- 58% of Americans own stocks, yet most have no systematic way to monitor them
- Wall Street professionals have Bloomberg terminals, research desks, and full-time analysts
- Retail investors rely on fragmented sources — Reddit, CNBC, Google News — none personalized to *their* holdings
- By the time a retail investor reads about a move, it has already happened

**The gap:**
> A retail investor who owns Apple, NVIDIA, and Meta has no way to wake up and know — in 2 minutes — what happened to those three stocks, why, and what to do next.

---

## Slide 3 — The Solution

**MarketMind closes that gap.**

Every morning at 6 AM ET, the system:

1. Fetches and scrapes full-text news for all user holdings
2. Scores macro headlines for relevance to each user's specific portfolio
3. Generates a Seeking Alpha-style analyst brief using GPT-4o
4. Produces a BUY / WAIT / SELL signal with rationale per stock
5. Converts the entire brief to a podcast-style audio file via OpenAI TTS

**Result:** A retail investor wakes up to the same quality of morning briefing that a professional trader would hand-craft — in their inbox before the 9:30 AM market open.

**Who it's for:** Someone who takes their investments seriously but has a job, a life, and no Bloomberg terminal.

---

## Slide 4 — System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DAILY PIPELINE (6 AM ET)                │
│  Cloud Scheduler → Cloud Run Job → run_daily.py             │
│                                                              │
│  [1] Firestore → load user portfolios                        │
│  [2] NewsAPI + Finnhub → fetch news → scrape full text       │
│       → embed (text-embedding-3-small) → Qdrant              │
│  [3] RSS feeds + Finnhub → macro news                        │
│  [4] GPT-4o → brief + signals → Firestore cache             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     STREAMLIT APP (on-demand)               │
│                                                              │
│  Auth → Firestore    Daily Brief page → cached brief        │
│                      Stock Research → 5-agent pipeline       │
│                      Portfolio → yfinance P&L               │
└─────────────────────────────────────────────────────────────┘

         Qdrant Cloud          Google Firestore
       (news + SEC vectors)    (users, portfolios, briefs)
```

**Two decoupled systems:** a scheduled pipeline that pre-generates work, and a Streamlit app that serves it instantly.

---

## Slide 5 — Feature: Daily Brief

**What the user sees every morning:**

| Component | What it shows |
|-----------|--------------|
| Portfolio Snapshot | P&L, daily % change, total value, per-stock metrics |
| Analyst Summary | 3-paragraph GPT-4o brief: market read, deep dive, what to watch |
| BUY / WAIT / SELL | Per-stock signal with 3-sentence analyst rationale and price level |
| Macro Alerts | World/market headlines scored 0–10 for portfolio relevance |
| Listen Mode | OpenAI TTS audio — `onyx` voice, 0.95x speed — full brief as podcast |
| Further Reading | Source links from NewsAPI articles (filtered from Qdrant by `has_url=True`) |

**Prompt engineering highlights:**
- System prompt instructs GPT-4o to write in the style of Seeking Alpha's Wall Street Breakfast
- 5 most-recent articles per ticker passed as context (up to 1,500 chars full text each)
- Model forbidden from fabricating prices, headlines, or estimates not in the data
- Signal prompts include few-shot examples to anchor the voice: crisp, specific, price-level aware

---

## Slide 6 — Feature: Stock Research (5-Agent Pipeline)

**Enter any ticker → get a research-grade deep dive**

```
User enters ticker
       │
       ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Agent 1     │  │  Agent 2     │  │  Agent 3     │
│  News Agent  │  │  SEC Agent   │  │  Financials  │
│  gpt-4o-mini │  │  gemini-2.5  │  │  gemini-2.5  │
│              │  │  RAG over    │  │  P/E, P/B,   │
│  Sentiment   │  │  10-K/10-Q   │  │  ROE, debt,  │
│  Key events  │  │  chunks in   │  │  volume      │
│  NewsAPI +   │  │  Qdrant      │  │  yfinance +  │
│  Finnhub     │  │              │  │  SEC EDGAR   │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       └──────────────────┴──────────────────┘
                          │
                          ▼
                 ┌──────────────┐
                 │  Agent 4     │
                 │  Synthesis   │
                 │  gpt-4o-mini │
                 │  300-word    │
                 │  unified     │
                 │  brief       │
                 └──────┬───────┘
                        │
                        ▼
               ┌─────────────────┐
               │  Agent 5        │
               │  Verdict Agent  │
               │  gpt-4o         │
               │  BUY/HOLD/SELL  │
               │  confidence 1-10│
               │  bull/bear case │
               │  key risks      │
               └─────────────────┘
```

All Agents 1–3 run in parallel via `asyncio.gather` — total latency is ~10–15s.

---

## Slide 7 — Data Pipeline: News Ingestion

**How news goes from API to LLM context:**

```
NewsAPI (20 articles/ticker)        Finnhub (30 articles/ticker)
        │                                    │
        ▼                                    ▼
  URL validation                    Headline + summary only
  trafilatura scrape                (no scraping — URLs unusable)
  (full article text)
        │                                    │
        └──────────────┬─────────────────────┘
                       ▼
              sha256(title + source + date)
              → hash_exists() check vs Qdrant
              → skip if already stored
                       │
                       ▼
              text-embedding-3-small (1536 dims)
              embed: title + description + full_text[:1000]
                       │
                       ▼
              Qdrant upsert
              Payload fields:
              - headline, description, full_text
              - tickers[], sectors[], source_api
              - has_url (bool), url
              - sentiment_label, sentiment_score
              - impact_score, published_at (unix)
              - content_hash (dedup key)
```

**Key design decisions:**
- `has_url` boolean indexed in Qdrant — source links filtered at DB level, not in Python
- Full article text stored (not just headline) — LLM gets up to 1,500 chars per article
- Content hash deduplication prevents duplicate storage across pipeline runs
- Batched fetching (5 tickers/batch, 1s delay) respects API rate limits

---

## Slide 8 — Vector Store & RAG

**Two Qdrant collections:**

| Collection | Content | Used for |
|------------|---------|----------|
| `news_articles` | All fetched news, embedded | Brief generation, source links |
| `sec_filings` | 10-K / 10-Q chunks (500 tokens, 50 overlap) | SEC Agent RAG |

**Retrieval strategy:**

- Daily brief: `scroll` ordered by `published_at DESC` with `has_url=True` filter for sources
- Stock research news: `query_points` (cosine similarity) filtered by ticker
- SEC Agent: 5 parallel RAG queries (risk factors, revenue outlook, debt, competition, capex), each retrieving top-8 chunks

**Embedding model:** `text-embedding-3-small` (OpenAI) — 1536 dimensions, cosine distance

---

## Slide 9 — Infrastructure & Deployment

```
┌─────────────────────────────────────────────────────────────┐
│                    Google Cloud Platform (us-east1)         │
│                                                             │
│  Cloud Scheduler ──→ Cloud Run Job                          │
│  cron: 0 6 * * 1-5      pipeline/run_daily.py               │
│  (6 AM ET, Mon–Fri)     Dockerfile (python:3.11-slim)       │
│                         PYTHONPATH=/app                     │
│                         ENV vars from Secret Manager        │
│                                                             │
│  Cloud Firestore                                            │
│  - users/{uid}/portfolio                                    │
│  - users/{uid}/briefs/{date}   ← daily brief cache          │
│                                                             │
│  Secret Manager                                             │
│  - OPENAI_API_KEY, GOOGLE_API_KEY, NEWSAPI_KEY              │
│  - FINNHUB_API_KEY, QDRANT_URL, QDRANT_API_KEY              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    External Services                        │
│                                                             │
│  Qdrant Cloud          OpenAI API         Google AI         │
│  (vector store)        GPT-4o, TTS        Gemini 2.5 Flash  │
│                                                             │
│  NewsAPI               Finnhub            SEC EDGAR         │
│  (full-text news)      (market data)      (10-K/10-Q)       │
└─────────────────────────────────────────────────────────────┘
```

**Auth:** Firebase Application Default Credentials on Cloud Run; service account JSON for local dev

---

## Slide 10 — Technical Highlights

**1. Async-first architecture**
Every I/O-bound operation uses `asyncio.gather` — news fetching, brief generation, and all 5 research agents run concurrently. A 5-stock portfolio brief generates in ~15s instead of ~75s sequential.

**2. Prompt engineering over fine-tuning**
No model fine-tuning. All voice/style is achieved through structured system prompts with few-shot examples. The brief sounds like Seeking Alpha because the prompt explicitly models that register — not because the model was trained on it.

**3. Deduplication at the data layer**
Content hash (`sha256(title + source + date)`) prevents re-embedding and re-storing articles across daily runs. Qdrant payload index on `content_hash` makes the lookup O(1).

**4. Brief caching with invalidation**
Generated briefs are cached in Firestore by `{uid}/{date}`. On regeneration, `delete_todays_brief(uid)` clears the cache first — guarantees the new brief reflects updated portfolio holdings.

**5. Source link reliability**
`has_url` is a Qdrant payload field (bool, indexed). Source links are retrieved with `FieldCondition(key="has_url", match=MatchValue(value=True))` — Finnhub articles (no usable URL) are excluded at the database level.

---

## Slide 11 — Limitations & Future Work

**Current limitations:**
- Scoped to top 50 US-listed stocks — no ETFs, international, or OTC
- News lookback: 7 days for research, 24 hours for daily brief
- Streamlit frontend is functional but not mobile-optimized
- No user authentication (Firebase Auth) — prototype uses simple user ID

**Planned improvements:**

| Enhancement | Approach |
|-------------|----------|
| Expand to full S&P 500 | Increase TOP_50 list + Qdrant cluster scaling |
| Price alerts | Cloud Run Service + WebSocket or email trigger |
| Portfolio performance charts | Plotly historical P&L over time from Firestore |
| Mobile app | React Native consuming a FastAPI backend |
| Multi-user Firebase Auth | Google/Email sign-in replacing the prototype ID form |
| Earnings calendar integration | Alpha Vantage or Polygon.io earnings API |

---

## Slide 12 — Summary

**MarketMind in one sentence:**
> An AI system that gives a retail investor the morning briefing quality of a professional analyst — personalized to their exact portfolio, delivered before market open.

**What was built:**
- End-to-end data pipeline: news fetch → scrape → embed → vector store
- Multi-LLM agent system: 5 specialized research agents + brief generation
- Automated daily pipeline on GCP Cloud Run (6 AM ET, Mon–Fri)
- Podcast-style audio brief via OpenAI TTS
- Full-stack Streamlit app with persistent user portfolios in Firestore

**Stack:** Python 3.11 · Streamlit · GPT-4o · Gemini 2.5 Flash · OpenAI TTS ·
LangChain · Qdrant Cloud · Google Cloud Firestore · Cloud Run · Cloud Scheduler

---

*Thank you — Questions?*
