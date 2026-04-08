import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    Range,
    VectorParams,
)
from config import EMBEDDING_DIMS, QDRANT_API_KEY, QDRANT_URL

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY if QDRANT_API_KEY else None
)

def init_collections() -> None:
    existing = {c.name for c in client.get_collections().collections}

    for name in ("news_articles", "sec_filings"):
        if name not in existing:
            client.create_collection(
                name,
                vectors_config=VectorParams(size=EMBEDDING_DIMS, distance=Distance.COSINE),
            )

    # Payload indexes for fast filtering
    _safe_create_index("news_articles", "published_at", "integer")
    _safe_create_index("news_articles", "tickers", "keyword")
    _safe_create_index("news_articles", "published_date", "keyword")
    _safe_create_index("news_articles", "content_hash", "keyword")
    _safe_create_index("sec_filings", "ticker", "keyword")
    _safe_create_index("sec_filings", "filing_type", "keyword")


def _safe_create_index(collection: str, field: str, schema_type: str) -> None:
    try:
        client.create_payload_index(collection, field, schema_type)
    except Exception:
        pass  # index already exists


# ── News helpers ──────────────────────────────────────────────────────────────

def hash_exists(content_hash: str) -> bool:
    results = client.scroll(
        "news_articles",
        scroll_filter=Filter(
            must=[FieldCondition(key="content_hash", match=MatchValue(value=content_hash))]
        ),
        limit=1,
    )[0]
    return len(results) > 0


def upsert_news_article(article: dict, vector: list[float]) -> None:
    if hash_exists(article["content_hash"]):
        return
    client.upsert(
        "news_articles",
        points=[PointStruct(id=str(uuid.uuid4()), vector=vector, payload=article)],
    )


def search_news(
    query_vector: list[float],
    tickers: list[str] | None = None,
    exclude_tickers: list[str] | None = None,
    date_from_unix: int | None = None,
    limit: int = 8,
) -> list[dict]:
    must, must_not = [], []
    if date_from_unix:
        must.append(FieldCondition(key="published_at", range=Range(gte=date_from_unix)))
    if tickers:
        must.append(FieldCondition(key="tickers", match=MatchAny(any=tickers)))
    if exclude_tickers:
        must_not.append(FieldCondition(key="tickers", match=MatchAny(any=exclude_tickers)))

    results = client.search(
        "news_articles",
        query_vector=query_vector,
        query_filter=Filter(must=must, must_not=must_not),
        limit=limit,
        with_payload=True,
    )
    return [r.payload for r in results]


# ── SEC helpers ───────────────────────────────────────────────────────────────

def upsert_sec_chunk(chunk: dict, vector: list[float]) -> None:
    client.upsert(
        "sec_filings",
        points=[PointStruct(id=str(uuid.uuid4()), vector=vector, payload=chunk)],
    )


def sec_chunks_exist(ticker: str, filing_type: str = "10-K") -> bool:
    results = client.scroll(
        "sec_filings",
        scroll_filter=Filter(
            must=[
                FieldCondition(key="ticker", match=MatchValue(value=ticker)),
                FieldCondition(key="filing_type", match=MatchValue(value=filing_type)),
            ]
        ),
        limit=1,
    )[0]
    return len(results) > 0


def search_sec_chunks(
    query_vector: list[float],
    ticker: str,
    filing_type: str = "10-K",
    limit: int = 5,
) -> list[dict]:
    results = client.search(
        "sec_filings",
        query_vector=query_vector,
        query_filter=Filter(
            must=[
                FieldCondition(key="ticker", match=MatchValue(value=ticker)),
                FieldCondition(key="filing_type", match=MatchValue(value=filing_type)),
            ]
        ),
        limit=limit,
        with_payload=True,
    )
    return [r.payload for r in results]
