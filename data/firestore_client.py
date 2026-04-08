from config import db
from google.cloud import firestore
from datetime import date


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
