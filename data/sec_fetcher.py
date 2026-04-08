"""
Fetch SEC EDGAR filings, chunk them, embed, and store in Qdrant.
Always includes SEC_USER_AGENT header and rate-limit delays.
"""
import time
import requests
from langchain.text_splitter import RecursiveCharacterTextSplitter

from config import (
    SEC_CHUNK_OVERLAP,
    SEC_CHUNK_SIZE,
    SEC_RATE_LIMIT_DELAY,
    SEC_USER_AGENT,
)
from data.qdrant_client import sec_chunks_exist, upsert_sec_chunk
from utils.embeddings import embed_batch

HEADERS = {
    "User-Agent": SEC_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
}

_CIK_CACHE: dict[str, str] = {}


def _get_cik(ticker: str) -> str:
    """Resolve ticker to zero-padded 10-digit CIK."""
    ticker_upper = ticker.upper()
    if ticker_upper in _CIK_CACHE:
        return _CIK_CACHE[ticker_upper]

    time.sleep(SEC_RATE_LIMIT_DELAY)
    r = requests.get(
        "https://www.sec.gov/files/company_tickers.json",
        headers=HEADERS,
        timeout=15,
    )
    r.raise_for_status()
    for entry in r.json().values():
        if entry["ticker"].upper() == ticker_upper:
            cik = str(entry["cik_str"]).zfill(10)
            _CIK_CACHE[ticker_upper] = cik
            return cik
    raise ValueError(f"CIK not found for {ticker}")


def _detect_section(text: str) -> str:
    t = text.lower()
    if "risk factor" in t:
        return "Risk Factors"
    if "revenue" in t or "net income" in t:
        return "Financial Results"
    if "competition" in t:
        return "Competition"
    if "outlook" in t or "guidance" in t:
        return "Outlook"
    return "General"


def fetch_and_embed_sec_filing(ticker: str, filing_type: str = "10-K") -> int:
    """
    Fetch latest SEC filing for ticker, chunk, embed, store in Qdrant.
    Returns number of chunks stored, or -1 if already cached.
    """
    if sec_chunks_exist(ticker, filing_type):
        return -1

    cik = _get_cik(ticker)

    time.sleep(SEC_RATE_LIMIT_DELAY)
    r = requests.get(
        f"https://data.sec.gov/submissions/CIK{cik}.json",
        headers=HEADERS,
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()

    filings = data.get("filings", {}).get("recent", {})
    forms   = filings.get("form", [])
    docs    = filings.get("primaryDocument", [])
    dates   = filings.get("filingDate", [])
    accs    = filings.get("accessionNumber", [])

    idx = next((i for i, f in enumerate(forms) if f == filing_type), None)
    if idx is None:
        return 0

    acc          = accs[idx].replace("-", "")
    doc          = docs[idx]
    filing_date  = dates[idx]

    # Build direct archive URL
    cik_nodot = cik.lstrip("0")
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_nodot}/{acc}/{doc}"

    time.sleep(SEC_RATE_LIMIT_DELAY)
    text_r = requests.get(url, headers=HEADERS, timeout=30)
    text_r.raise_for_status()
    raw_text = text_r.text

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=SEC_CHUNK_SIZE, chunk_overlap=SEC_CHUNK_OVERLAP
    )
    chunks = splitter.split_text(raw_text)
    if not chunks:
        return 0

    # Embed in batches of 100
    all_vectors: list[list[float]] = []
    batch_size = 100
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        all_vectors.extend(embed_batch(batch))

    for i, (chunk, vector) in enumerate(zip(chunks, all_vectors)):
        upsert_sec_chunk(
            {
                "ticker": ticker,
                "filing_type": filing_type,
                "filing_date": filing_date,
                "section": _detect_section(chunk),
                "text": chunk,
                "chunk_index": i,
                "total_chunks": len(chunks),
            },
            vector,
        )

    return len(chunks)
