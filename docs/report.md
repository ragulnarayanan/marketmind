# MarketMind: AI-Powered Portfolio Intelligence for Retail Investors

**Project Report**

---

## 1. Introduction

Retail participation in financial markets has grown significantly over the past decade, yet the tools available to individual investors have not kept pace with the sophistication of institutional players. Professional traders begin each morning with curated research, analyst notes, macro summaries, and portfolio-specific alerts — produced by dedicated research desks with access to Bloomberg terminals, proprietary data feeds, and real-time news aggregation. A retail investor, by contrast, must manually piece together information from disparate sources: financial news websites, brokerage apps, social media, and earnings calendars — none of which are personalized to their specific holdings.

MarketMind addresses this gap by building an AI-driven system that generates a daily, personalized portfolio brief for retail investors. The brief is structured, analyst-quality, delivered before market open, and available as both a readable summary and a podcast-style audio file. The system integrates multi-source news ingestion, vector-based retrieval, large language model (LLM) orchestration, and automated cloud infrastructure to produce an end-to-end product that functions without user intervention once configured.

---

## 2. Problem Statement and Motivation

### 2.1 The Retail Investor's Information Gap

The fundamental challenge for a retail investor is not a lack of financial data — it is a lack of synthesis. Headlines are abundant; contextualized, portfolio-specific analysis is not. Consider an investor who holds Apple, NVIDIA, and JPMorgan. On any given morning, each company may have produced earnings news, analyst rating changes, sector-level macro developments, or geopolitical events that affect their holdings differently. Assembling that picture manually, understanding the cross-holding implications, and forming an actionable view requires hours of reading — time most retail investors do not have.

### 2.2 Existing Solutions and Their Shortcomings

Current tools available to retail investors fall into three categories:

- **General market news apps** (CNBC, Bloomberg, Yahoo Finance): Not personalized to individual holdings. High noise-to-signal ratio.
- **Brokerage apps** (Robinhood, Fidelity): Provide basic price data and news feeds, but do not synthesize or contextualize information into actionable guidance.
- **AI chat tools** (ChatGPT, Perplexity): Can answer questions on demand, but require the user to prompt them, have no awareness of the user's specific portfolio, and do not run automatically each morning.

None of these tools deliver a pre-generated, portfolio-aware, analyst-style brief before market open.

### 2.3 Design Goals

MarketMind was designed to meet the following requirements:

1. **Personalization:** Analysis must be specific to the user's exact holdings — not generic market commentary.
2. **Automation:** The brief must be generated and ready before the market opens without user action.
3. **Quality:** The output must read and sound like professional analyst work, not summarized headlines.
4. **Accessibility:** The brief must be consumable in under 2 minutes — as text or audio — on any device.
5. **Transparency:** Source links must be provided so users can verify and read further.

---

## 3. System Design and Architecture

MarketMind is composed of two decoupled subsystems: a scheduled data pipeline that runs at 6 AM ET on weekdays, and an interactive Streamlit web application that serves users on demand.

### 3.1 Overall Architecture

```
Cloud Scheduler (6 AM ET, Mon–Fri)
        │
        ▼
Cloud Run Job — run_daily.py
  Phase 1: Load user portfolios from Firestore
  Phase 2: Fetch news (NewsAPI + Finnhub) → scrape → embed → Qdrant
  Phase 3: Fetch macro/world news (RSS + Finnhub general)
  Phase 4: Generate briefs for all users → cache in Firestore

Streamlit App (on-demand)
  ├── Daily Brief page   → reads Firestore cache, renders brief + audio
  ├── Stock Research     → runs 5-agent pipeline on demand
  └── Portfolio page     → yfinance P&L across holdings
```

All persistent state lives in two stores: **Google Cloud Firestore** for user data (portfolios, cached briefs) and **Qdrant Cloud** for vector embeddings (news articles and SEC filing chunks).

### 3.2 Data Pipeline

#### News Ingestion

The pipeline fetches news from two sources per ticker:

- **NewsAPI** (primary): Returns up to 20 articles per ticker with real URLs. Each URL is validated and then scraped for full article text using `trafilatura`. The scraped text, headline, and description are combined and embedded using OpenAI's `text-embedding-3-small` (1,536 dimensions).

- **Finnhub** (secondary): Returns headlines and summaries only. URLs from Finnhub are not reliably scrapeable, so no full text is stored. These articles contribute to news context but are excluded from source links.

Before embedding and storing any article, a content hash (`sha256(title + source + published_date)`) is computed and checked against Qdrant. This deduplication mechanism prevents re-processing the same article across pipeline runs, which is critical for keeping Qdrant's collection size bounded and avoiding duplicate context in LLM prompts.

Each stored article carries a rich payload:
```
headline, description, full_text, url, has_url (bool),
source_name, tickers[], sectors[], sentiment_label,
sentiment_score, impact_score, published_at (unix timestamp),
content_hash, source_api
```

The `has_url` boolean is stored as a Qdrant payload index, allowing the brief generator to retrieve only articles with usable URLs at the database level — a key optimization over filtering in Python after retrieval.

#### Macro News

Macro and world news is fetched from six RSS feeds (Reuters, BBC, WSJ, FT, Oil Price) and Finnhub's general news endpoint. These articles are not tagged to specific tickers; instead, they carry `tickers=[]` and `sectors=["macro"]`. At brief generation time, a separate macro scoring step uses GPT-4o-mini to score each headline 0–10 for relevance to the user's specific portfolio and return only items scoring 6 or above.

### 3.3 Daily Brief Generation

For each user, brief generation runs as a multi-step async pipeline:

**Step 1 — Portfolio snapshot:** Current prices and P&L are fetched from yfinance for each holding. Daily percentage change and total P&L from cost basis are computed.

**Step 2 — Qdrant retrieval:** The 10 most recent articles per ticker are retrieved from Qdrant (ordered by `published_at DESC`). Full text (up to 1,500 characters) is passed to the LLM for each article.

**Step 3 — Portfolio summary (GPT-4o):** A system prompt instructs GPT-4o to write in the voice of a Seeking Alpha analyst. The prompt specifies a three-paragraph structure: (1) market and portfolio read with specific movers and catalysts, (2) deep dive on the 2–3 most important stories with cross-holding connections, (3) key variables to watch in the next 48–72 hours with specific price levels. The model is forbidden from fabricating data not present in the input.

**Step 4 — Per-stock signals (GPT-4o):** For each holding, a separate call generates a BUY / WAIT / SELL signal with a three-sentence analyst rationale including the key catalyst, price context, and next action. Few-shot examples in the prompt anchor the model to the desired voice.

**Step 5 — Macro alerts (GPT-4o-mini):** The top 40 macro headlines are scored for portfolio relevance. Each relevant item receives a one-sentence `why_matters` explanation naming the specific ticker and mechanism of impact.

**Step 6 — Source links:** A Qdrant scroll filtered by both ticker and `has_url=True` retrieves up to 15 URLs per ticker. De-duplicated across tickers and capped at 15 total links for the brief.

**Step 7 — Audio brief (OpenAI TTS):** The brief dict is converted to a spoken script by `write_audio_script()`. Tickers are replaced with natural spoken company names (e.g., `AAPL` → "Apple") using a lookup dictionary. The script is passed to OpenAI's `tts-1` model with the `onyx` voice at 0.95x speed, returning raw MP3 bytes served directly to the browser via `st.audio()`.

**Step 8 — Caching:** The completed brief is stored in Firestore at `users/{uid}/briefs/{date}`. On subsequent visits the same day, the cached brief is returned instantly. When a user regenerates, `delete_todays_brief(uid)` clears the cache before re-running.

Steps 3, 4, and 5 run in parallel via `asyncio.gather`, reducing latency significantly.

### 3.4 Stock Research Pipeline (5-Agent System)

The stock research feature runs five specialized agents in parallel:

| Agent | Model | Data Source | Output |
|-------|-------|-------------|--------|
| News Agent | GPT-4o-mini | NewsAPI + Finnhub via Qdrant | Sentiment label, key events summary |
| SEC Agent | Gemini 2.5 Flash | 10-K/10-Q chunks via Qdrant RAG | Risk factors, revenue outlook, debt, competition, capex |
| Financials Agent | Gemini 2.5 Flash | yfinance + SEC EDGAR | P/E, P/B, ROE, debt ratio, volume spike analysis |
| Synthesis Agent | GPT-4o-mini | Outputs of Agents 1–3 | 300-word unified research brief |
| Verdict Agent | GPT-4o | Synthesis brief | BUY/HOLD/SELL, confidence 1–10, bull case, bear case, key risks |

The SEC Agent uses retrieval-augmented generation (RAG). 10-K and 10-Q filings are chunked at 500 tokens with 50-token overlap, embedded, and stored in a separate Qdrant collection (`sec_filings`). At query time, five predefined questions (risk factors, revenue outlook, debt, competitive threats, capital allocation) are each answered with the top-8 most relevant chunks retrieved by cosine similarity.

Agents 1–3 run concurrently. Agent 4 waits for all three, then Agent 5 waits for Agent 4. Total end-to-end latency for the full research pipeline is approximately 10–20 seconds.

### 3.5 Infrastructure

The system is deployed entirely on Google Cloud Platform in the `us-east1` region:

- **Cloud Run Job** hosts the daily pipeline. The container is built from a `python:3.11-slim` Dockerfile with `PYTHONPATH=/app` to support project-root imports.
- **Cloud Scheduler** triggers the job at `0 6 * * 1-5` (6 AM ET, Monday–Friday) with the `America/New_York` timezone.
- **Secret Manager** stores all API keys. Secrets are injected as environment variables at container runtime.
- **Firebase Authentication** is handled using Application Default Credentials on Cloud Run (no JSON file in the container). Local development uses a service account JSON file with an `os.path.exists()` fallback.
- **Firestore** (Firebase) stores user records, portfolios, and the daily brief cache.

---

## 4. Implementation Details

### 4.1 Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | Streamlit | Rapid prototyping; Python-native; no separate frontend codebase |
| LLM — reasoning | OpenAI GPT-4o | Best-in-class reasoning for final verdict and portfolio summary |
| LLM — fast tasks | OpenAI GPT-4o-mini | Cost-effective for signal generation, macro scoring, news synthesis |
| LLM — long context | Google Gemini 2.5 Flash | 1M context window ideal for SEC filings; strong structured output |
| Text-to-Speech | OpenAI TTS `tts-1` | High-quality, low-latency; `onyx` voice natural for financial content |
| Embeddings | OpenAI `text-embedding-3-small` | Strong retrieval quality; 1,536 dims; cost-effective |
| Vector store | Qdrant Cloud | Payload filtering (has_url, ticker, date range); fast scroll + search |
| User data | Google Cloud Firestore | Flexible NoSQL; native GCP integration; real-time capable |
| Financial data | yfinance + SEC EDGAR | Free, reliable for price data and regulatory filings |
| News | NewsAPI + Finnhub | NewsAPI for full-text scrapeable articles; Finnhub for market-specific coverage |
| Web scraping | trafilatura | Best-in-class article extraction; handles boilerplate detection |
| Orchestration | LangChain + asyncio | Agent chaining; async parallelism for latency reduction |
| Pipeline | GCP Cloud Run + Cloud Scheduler | Serverless; scales to zero; no always-on cost |

### 4.2 Prompt Engineering

No fine-tuning was performed. All model behavior is controlled through prompt design:

- **Voice anchoring:** The portfolio summary prompt specifies Seeking Alpha's *Wall Street Breakfast* as the target register. Style cues are explicit: preferred active verbs, forbidden filler phrases, and required structural elements (three paragraphs, specific roles per paragraph).
- **Few-shot examples:** The signal generation prompt includes three complete examples of the desired output voice, each demonstrating how to name a catalyst, reference a price level, and give a specific next action.
- **Grounding:** All prompts include `STRICT: Only use facts from the data provided. Do not fabricate prices, headlines, or estimates.` to prevent hallucination.
- **Structured output:** All LLM calls return JSON, parsed by a shared `parse_llm_json()` utility that strips markdown fences before parsing.

### 4.3 Key Design Decisions

**Batch pipeline vs. on-demand generation:** Brief generation is done at 6 AM by a scheduled job rather than on first page load. This decouples latency from the user experience — the brief is instant when the user opens the app. The trade-off is that the brief reflects news available at 6 AM, not real-time.

**Full article text over headlines:** NewsAPI articles are scraped for full text using trafilatura. The brief generator receives up to 1,500 characters per article (5 articles per ticker), giving the LLM substantially more signal than a headline and 200-character description would provide.

**Dual Qdrant scroll strategy:** For the brief summary, articles are retrieved by ticker with no URL filter (Finnhub articles contribute news context even without URLs). For source links, a separate scroll adds `has_url=True` as a Qdrant filter — this ensures source links only contain real, scrapeable URLs, without penalizing the news context with the same restriction.

---

## 5. Results and Observations

### 5.1 Output Quality

The system consistently produces structured, coherent briefs that cover the correct holdings with relevant news. The Seeking Alpha-style prompting produces notably more specific output than generic "summarize this news" prompting — generated text includes specific price levels, percentage moves, and named catalysts rather than vague sentiment descriptions.

The BUY / WAIT / SELL signals are contextually grounded in the user's cost basis and current price, not just news sentiment, which makes them more actionable for an investor tracking their actual P&L.

### 5.2 Latency

- Daily brief (pre-cached): < 1 second (Firestore read)
- Daily brief (generation): 15–25 seconds (async parallel — portfolio summary + signals + macro alerts)
- Stock research pipeline: 10–20 seconds (5 agents, phases 1–3 parallel)
- Audio brief generation: 3–6 seconds (OpenAI TTS)

### 5.3 Pipeline Reliability

The pipeline handles failures gracefully: each agent has try/except with fallback returns, batch news fetching logs failures per ticker without stopping the run, and Qdrant upserts are idempotent (content hash deduplication). In practice, the most common failure mode is NewsAPI rate limits on the free tier for high-frequency runs.

---

## 6. Limitations

- **Universe:** Currently scoped to 50 US-listed large-cap stocks. ETFs, international markets, small-caps, and crypto are not supported.
- **News timeliness:** The daily pipeline runs once at 6 AM. Breaking news after that time is not reflected until the next day or manual regeneration.
- **SEC filing freshness:** SEC chunks are embedded when first requested. Filings are not automatically re-fetched when a company publishes a new 10-K.
- **Authentication:** The current app uses a simple user ID form — not production-ready Firebase Authentication with email/Google sign-in.
- **Mobile experience:** The Streamlit app is not optimized for mobile. The audio brief partially compensates for this by enabling eyes-free consumption.
- **Hallucination risk:** Despite grounding instructions, GPT-4o can occasionally generate plausible-sounding but unverified claims when input data is sparse. Source links are provided so users can verify.

---

## 7. Future Work

1. **Expand universe to S&P 500:** Scale Qdrant cluster and pipeline batching to support 500 tickers. NewsAPI rate limits would require a paid tier.
2. **Price alert system:** Triggered Cloud Run Service that monitors intraday price movements and sends email/push notifications when holdings hit user-defined thresholds.
3. **Historical performance tracking:** Store P&L snapshots in Firestore daily and visualize portfolio performance over time with Plotly.
4. **Mobile application:** React Native client consuming a FastAPI backend wrapping the existing Python logic.
5. **Production authentication:** Replace the prototype user ID form with Firebase Auth (Google OAuth + email/password).
6. **Earnings calendar integration:** Flag upcoming earnings dates in the brief and adjust signal urgency accordingly.
7. **Real-time brief refresh:** WebSocket-based brief update triggered by significant price moves during market hours.

---

## 8. Conclusion

MarketMind demonstrates that the quality gap between institutional and retail investor tooling can be substantially closed with modern LLM capabilities and cloud infrastructure. The key insight driving the system is that retail investors do not lack data — they lack synthesis. By combining multi-source news ingestion, vector-based retrieval, multi-LLM agent orchestration, and automated scheduling, the system delivers a morning briefing that is genuinely personalized, analyst-quality, and consumable before the market opens.

The architectural choices — decoupled pipeline and app, async-first agent execution, vector store with payload filtering, full-text article scraping — reflect deliberate trade-offs between latency, quality, and cost. The result is a system that feels instant to the user while producing substantive, grounded analysis behind the scenes.

The project is open-source at [github.com/ragulnarayanan/marketmind](https://github.com/ragulnarayanan/marketmind).

---

*Ragul Narayanan Magesh · Northeastern University · April 2026*
