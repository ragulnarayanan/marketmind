from config import db, GCS_BUCKET_NAME
from google.cloud import firestore, storage
from datetime import date

_gcs = storage.Client()


def _gcs_audio_path(uid: str, date_str: str) -> str:
    return f"audio_briefs/{uid}/{date_str}.mp3"


def get_user(uid: str) -> dict | None:
    ref  = db.collection("users").document(uid)
    snap = ref.get()
    return snap.to_dict() if snap.exists else None


def get_or_create_user(uid: str, email: str, display_name: str) -> dict:
    ref = db.collection("users").document(uid)
    if not ref.get().exists:
        ref.set({
            "email": email,
            "display_name": display_name,
            "tier": "free",
            "created_at": firestore.SERVER_TIMESTAMP,
        })
    return ref.get().to_dict()


def get_portfolio(uid: str) -> list[dict]:
    docs = db.collection("users").document(uid).collection("portfolio").stream()
    return [d.to_dict() for d in docs]


def upsert_holding(uid: str, ticker: str, qty: float, avg_cost: float) -> None:
    db.collection("users").document(uid).collection("portfolio").document(ticker).set({
        "ticker": ticker,
        "qty": qty,
        "avg_cost": avg_cost,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })


def remove_holding(uid: str, ticker: str) -> None:
    db.collection("users").document(uid).collection("portfolio").document(ticker).delete()


def get_watchlist(uid: str) -> list[str]:
    docs = db.collection("users").document(uid).collection("watchlist").stream()
    return [d.to_dict()["ticker"] for d in docs]


def add_to_watchlist(uid: str, ticker: str) -> None:
    db.collection("users").document(uid).collection("watchlist").document(ticker).set({
        "ticker": ticker,
        "added_at": firestore.SERVER_TIMESTAMP,
    })


def remove_from_watchlist(uid: str, ticker: str) -> None:
    db.collection("users").document(uid).collection("watchlist").document(ticker).delete()


def get_todays_brief(uid: str) -> dict | None:
    doc = (
        db.collection("users")
        .document(uid)
        .collection("briefs")
        .document(str(date.today()))
        .get()
    )
    return doc.to_dict() if doc.exists else None


def store_brief(uid: str, brief: dict) -> None:
    db.collection("users").document(uid).collection("briefs").document(
        str(date.today())
    ).set(brief)


def delete_todays_brief(uid: str) -> None:
    db.collection("users").document(uid).collection("briefs").document(
        str(date.today())
    ).delete()


def get_todays_audio(uid: str) -> bytes | None:
    """Download today's audio MP3 from GCS. Returns None if not yet generated."""
    date_str  = str(date.today())
    blob_name = _gcs_audio_path(uid, date_str)
    try:
        bucket = _gcs.bucket(GCS_BUCKET_NAME)
        blob   = bucket.blob(blob_name)
        if not blob.exists():
            return None
        return blob.download_as_bytes()
    except Exception:
        return None


def save_todays_audio(uid: str, audio_bytes: bytes) -> None:
    """Upload today's audio MP3 to GCS."""
    date_str  = str(date.today())
    blob_name = _gcs_audio_path(uid, date_str)
    bucket    = _gcs.bucket(GCS_BUCKET_NAME)
    blob      = bucket.blob(blob_name)
    blob.upload_from_string(audio_bytes, content_type="audio/mpeg")


def delete_todays_audio(uid: str) -> None:
    """Delete today's audio MP3 from GCS."""
    date_str  = str(date.today())
    blob_name = _gcs_audio_path(uid, date_str)
    try:
        bucket = _gcs.bucket(GCS_BUCKET_NAME)
        blob   = bucket.blob(blob_name)
        if blob.exists():
            blob.delete()
    except Exception:
        pass


def get_brief_history(uid: str, days: int = 30) -> list[dict]:
    docs = (
        db.collection("users")
        .document(uid)
        .collection("briefs")
        .order_by("generated_at", direction=firestore.Query.DESCENDING)
        .limit(days)
        .stream()
    )
    return [d.to_dict() for d in docs]
