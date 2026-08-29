import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))

MISTRAL_API_KEY = os.getenv("LLM_API_KEY")
EMBEDDING_MODEL = "mistral-embed"
EMBEDDING_ENDPOINT = "https://api.mistral.ai/v1/embeddings"


def get_embedding(text: str) -> list[float]:
    """Generate a 1024-dim embedding vector using Mistral's embedding API."""
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": EMBEDDING_MODEL,
        "input": [text]
    }
    res = requests.post(EMBEDDING_ENDPOINT, json=payload, headers=headers, timeout=10.0)
    if res.status_code == 200:
        return res.json()["data"][0]["embedding"]
    else:
        raise RuntimeError(f"Embedding API failed ({res.status_code}): {res.text}")


def get_embeddings_batch(texts: list[str], batch_size: int = 10) -> list[list[float]]:
    """Generate embeddings for a list of texts in batches."""
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": EMBEDDING_MODEL,
            "input": batch
        }
        res = requests.post(EMBEDDING_ENDPOINT, json=payload, headers=headers, timeout=30.0)
        if res.status_code == 200:
            data = res.json()["data"]
            # Sort by index to maintain order
            data.sort(key=lambda x: x["index"])
            all_embeddings.extend([d["embedding"] for d in data])
        else:
            raise RuntimeError(f"Embedding API failed ({res.status_code}): {res.text}")
    return all_embeddings
