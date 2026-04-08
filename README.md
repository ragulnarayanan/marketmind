# MarketMind

AI-powered stock research and daily portfolio brief app.

## What it does

**Stock Research** — Enter any ticker. Five specialized AI agents (powered by GPT-4o, GPT-4o-mini, Gemini 1.5 Pro, and Gemini 1.5 Flash) research the stock across news, SEC filings, and financials, then return a unified Buy / Hold / Sell verdict.

**Daily Portfolio Brief** — Maintain a persistent portfolio and watchlist. Every day the app generates a personalized brief: portfolio P&L, per-stock news summaries, macro news filtered for relevance to your holdings, and a Buy / Wait / Sell signal per holding.

## Tech stack

- **Frontend**: Streamlit
- **LLMs**: OpenAI (`gpt-4o`, `gpt-4o-mini`) + Google (`gemini-1.5-pro`, `gemini-1.5-flash`)
- **Orchestration**: LangChain
- **User data**: Google Cloud Firestore
- **Vector store**: Qdrant
- **News sources**: NewsAPI + Finnhub
- **Financial data**: yfinance + SEC EDGAR

## Setup

### 1. Prerequisites

- Python 3.11+
- Docker (for Qdrant)
- GCP project with Firestore enabled (see spec for full GCP/Firebase setup)
- API keys for OpenAI, Google AI, NewsAPI, Finnhub

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys and GCP credentials
```

Place your `gcp-service-account.json` in the project root (never commit this file).

### 4. Start Qdrant

```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 5. Verify all connections

```bash
python verify_setup.py
```

### 6. Run the app

```bash
streamlit run app.py
```

For local dev, add `TEST_UID=your-test-id` to `.env` to skip the login form.

## Agent architecture

| Agent | Model | Role |
|-------|-------|------|
| News Agent | gpt-4o-mini | Sentiment + key events from NewsAPI/Finnhub |
| SEC Agent | gemini-1.5-pro | RAG over 10-K/10-Q filing chunks (1M context) |
| Financials Agent | gemini-1.5-flash | P/E, P/B, ROE, debt, volume spikes |
| Synthesis Agent | gpt-4o-mini | 300-word unified research brief |
| Verdict Agent | gpt-4o | Final Buy / Hold / Sell with confidence score |

All agents run phases 1-3 with async parallelism via `asyncio.gather`.

## GCP region

All services use `us-east1` (South Carolina). Do not mix regions — cross-region calls add latency and egress charges.

## Security

- Never commit `.env` or `gcp-service-account.json`
- Set a GCP billing budget alert at $10 (Billing → Budgets & alerts)
- The Blaze (pay-as-you-go) Firebase plan is required for Cloud Run and external API calls
