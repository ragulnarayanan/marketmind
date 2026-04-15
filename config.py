
import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY  = os.getenv("GOOGLE_API_KEY")
NEWSAPI_KEY     = os.getenv("NEWSAPI_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
SEC_USER_AGENT  = os.getenv(
    "SEC_USER_AGENT",
    "Ragul Narayanan Magesh magesh.ra@northeastern.edu"
)

# ── GCP ───────────────────────────────────────────────────────────────────────
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_REGION     = os.getenv("GCP_REGION", "us-east1")

# ── Qdrant ────────────────────────────────────────────────────────────────────
QDRANT_URL     = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")   # None if not set — fine for local

# ── Models ────────────────────────────────────────────────────────────────────
GPT_FAST     = "gpt-4o-mini"       # news, synthesis, stock brief, buy/wait
GPT_SMART    = "gpt-4o"            # final verdict only
GEMINI_FAST  = "gemini-2.5-flash"   # financials, structured analysis
GEMINI_PRO   = "gemini-2.5-flash"   # SEC RAG, macro filter (long context)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMS  = int(os.getenv("EMBEDDING_DIMS", "1536"))

# ── App Constants ─────────────────────────────────────────────────────────────
SPIKE_THRESHOLD      = 2.0    # volume spike ratio flag
MACRO_RELEVANCE_MIN  = 5      # min score to include macro item in brief
NEWS_LOOKBACK_DAYS   = 7      # for stock research agent
BRIEF_LOOKBACK_HOURS = 24     # for daily brief news fetch
SEC_CHUNK_SIZE       = 500    # tokens per SEC filing chunk
SEC_CHUNK_OVERLAP    = 50     # overlap between chunks
TOP_K_VECTOR_RESULTS = 8      # Qdrant search limit
SEC_RATE_LIMIT_DELAY = 0.15   # seconds between SEC EDGAR requests

# ── Startup validation — fail loudly if any required key is missing ───────────
_required = {
    "OPENAI_API_KEY":  OPENAI_API_KEY,
    "GOOGLE_API_KEY":  GOOGLE_API_KEY,
    "NEWSAPI_KEY":     NEWSAPI_KEY,
    "FINNHUB_API_KEY": FINNHUB_API_KEY,
}
_missing = [k for k, v in _required.items() if not v]
if _missing:
    raise EnvironmentError(
        f"\nMissing required environment variables: {', '.join(_missing)}\n"
        f"Copy .env.example to .env and fill in the values.\n"
    )

# ── Firebase / Firestore ──────────────────────────────────────────────────────
if not firebase_admin._apps:
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./gcp-service-account.json")
    sa_json   = os.getenv("GCP_SERVICE_ACCOUNT_JSON")  # Streamlit Cloud secret

    if sa_json:
        # Streamlit Cloud — JSON stored as env var, write to temp file
        import json as _json
        import tempfile
        _tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        _tmp.write(sa_json)
        _tmp.close()
        cred = credentials.Certificate(_tmp.name)
    elif os.path.exists(cred_path):
        # Local dev — use service account JSON file
        cred = credentials.Certificate(cred_path)
    else:
        # Cloud Run — use Application Default Credentials
        cred = credentials.ApplicationDefault()

    firebase_admin.initialize_app(cred, {"projectId": GCP_PROJECT_ID})

db = firestore.client()

# ── Google Gemini client (new google-genai package) ───────────────────────────
from google import genai as google_genai
GOOGLE_CLIENT = google_genai.Client(api_key=GOOGLE_API_KEY)