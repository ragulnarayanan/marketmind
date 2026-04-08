import time
import openai
from config import OPENAI_API_KEY, EMBEDDING_MODEL

client = openai.OpenAI(api_key=OPENAI_API_KEY)


def embed_text(text: str) -> list[float]:
    """Embed a single text string via OpenAI."""
    text = text.replace("\n", " ").strip()
    if not text:
        return [0.0] * 1536
    for attempt in range(3):
        try:
            response = client.embeddings.create(
                input=text,
                model=EMBEDDING_MODEL,
            )
            return response.data[0].embedding
        except openai.RateLimitError:
            time.sleep(2 ** attempt)
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(1)
    return [0.0] * 1536


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts with retry logic."""
    cleaned = [t.replace("\n", " ").strip() for t in texts]
    for attempt in range(3):
        try:
            response = client.embeddings.create(
                input=cleaned,
                model=EMBEDDING_MODEL,
            )
            return [item.embedding for item in response.data]
        except openai.RateLimitError:
            time.sleep(2 ** attempt)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1)
    return [[0.0] * 1536 for _ in texts]
