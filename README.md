# MarketMind

> A daily briefing for retail investors who don't have time to be their own analyst — delivered in the voice of a financial podcast, in under 2 minutes.

**[Live Demo](https://ragulnarayanan-marketmind-app-u3eic9.streamlit.app/)**

## The problem

Most retail investors own a portfolio but have no real edge on it. They bought the stocks, but they can't track every earnings call, analyst note, or macro shift that moves their specific holdings. By the time they catch up, the move already happened. They're competing with people who read Bloomberg all day.

## What MarketMind does

Every morning, MarketMind reads the news, scores it against *your* portfolio, and hands you a brief that sounds like a Seeking Alpha analyst wrote it — what moved, why, what it means for *your* stocks, and what to watch today. Listen to it like a podcast on your commute, or read it in 2 minutes. Source links are there when you want to go deeper.

**Who it's for:** Someone who takes their investments seriously but has a job, a life, and no Bloomberg terminal.

> **Scope:** Currently built for the top 50 US-listed stocks. International exchanges, ETFs, crypto, and OTC markets are not supported.

---

### Daily Brief

A personalized morning brief generated fresh each day:

- **Portfolio snapshot** — P&L across all holdings, daily movers, total portfolio performance
- **Analyst-style summary** — three-paragraph breakdown in the voice of a financial podcast: market read, deep dive on key stories, and what to watch in the next 48 hours
- **Per-stock signals** — BUY / WAIT / SELL call with a 3-sentence analyst rationale and price level to watch
- **Macro alerts** — world and market news scored for relevance to your specific holdings, with one-line impact summaries
- **Listen mode** — full audio brief via OpenAI TTS, consumable on the go
- **Further reading** — source links to the actual articles behind the analysis

### Stock Research

Enter any ticker for a five-agent deep dive:

- News sentiment and key events
- SEC filing analysis (10-K / 10-Q)
- Financials (P/E, P/B, ROE, debt, volume)
- Unified research brief
- Final Buy / Hold / Sell verdict with confidence score

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit |
| LLMs | OpenAI `gpt-4o`, `gpt-4o-mini` · Google `gemini-2.5-flash` |
| Audio | OpenAI TTS (`tts-1`, `onyx` voice) |
| Orchestration | LangChain + `asyncio` |
| User data | Google Cloud Firestore |
| Vector store | Qdrant Cloud |
| News | NewsAPI (full article scrape via trafilatura) + Finnhub |
| Financial data | yfinance + SEC EDGAR |
| Pipeline | Cloud Run Jobs + Cloud Scheduler (6 AM ET, Mon–Fri) |

## Agent architecture

| Agent | Model | Role |
|-------|-------|------|
| News Agent | gpt-4o-mini | Sentiment + key events from NewsAPI / Finnhub |
| SEC Agent | gemini-2.5-flash | RAG over 10-K / 10-Q filing chunks |
| Financials Agent | gemini-2.5-flash | P/E, P/B, ROE, debt, volume spikes |
| Synthesis Agent | gpt-4o-mini | Unified research brief |
| Verdict Agent | gpt-4o | Final Buy / Hold / Sell with confidence score |

All agents run with async parallelism via `asyncio.gather`.

---

## Setup

### 1. Prerequisites

- Python 3.11+
- GCP project with Firestore enabled
- API keys for OpenAI, Google AI, NewsAPI, Finnhub, Qdrant Cloud

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Fill in your API keys and GCP project ID
```

All required keys are listed in [`.env.example`](.env.example) with descriptions. You will need accounts for: OpenAI, NewsAPI, Finnhub, Qdrant Cloud, and GCP (Firestore + Cloud Run).

Place your `gcp-service-account.json` in the project root for local dev. On Cloud Run, Application Default Credentials are used automatically.

### 4. Verify connections

```bash
python verify_setup.py
```

### 5. Run

```bash
streamlit run app.py
```

Set `TEST_UID=your-id` in `.env` to skip the login form during local development.

---

## Infrastructure notes

- **GCP region:** `us-east1` (South Carolina) for all services — do not mix regions
- **Pipeline:** Cloud Run Job triggered by Cloud Scheduler at `0 11 * * 1-5` (6 AM ET Mon–Fri)
- **Secrets:** All API keys stored in GCP Secret Manager, injected at runtime

