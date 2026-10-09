import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))

MISTRAL_API_KEY = os.getenv("LLM_API_KEY")
EMBEDDING_MODEL = "mistral-embed"
EMBEDDING_ENDPOINT = "https://api.mistral.ai/v1/embeddings"


def _embed(texts: list[str], timeout: float) -> list[list[float]]:
    res = requests.post(
        EMBEDDING_ENDPOINT,
        json={"model": EMBEDDING_MODEL, "input": texts},
        headers={"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"},
        timeout=timeout,
    )
    if res.status_code != 200:
        raise RuntimeError(f"Embedding API failed ({res.status_code}): {res.text}")
    data = sorted(res.json()["data"], key=lambda x: x["index"])
    return [d["embedding"] for d in data]


def get_embedding(text: str) -> list[float]:
    """Generate a 1024-dim embedding vector using Mistral's embedding API."""
    return _embed([text], timeout=10.0)[0]


def get_embeddings_batch(texts: list[str], batch_size: int = 10) -> list[list[float]]:
    """Generate embeddings for a list of texts in batches."""
    out = []
    for i in range(0, len(texts), batch_size):
        out.extend(_embed(texts[i:i + batch_size], timeout=30.0))
    return out
