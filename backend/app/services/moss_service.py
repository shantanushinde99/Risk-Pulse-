import os
import re
import time
import asyncio
from typing import Optional
from moss import MossClient, QueryOptions
from dotenv import load_dotenv
from app.services.embedding_service import get_embedding

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))

MOSS_PROJECT_ID = os.getenv("MOSS_PROJECT_ID")
MOSS_PROJECT_KEY = os.getenv("MOSS_PROJECT_KEY") or os.getenv("MOSS_API_KEY")
INDEX_NAME = "riskpulse-custom-context"
SEARCH_TIMEOUT_S = 8.0
REFRESH_S = 600  # matches load_index auto_refresh polling

CUSTOMER_ID_RE = re.compile(r"customer_id: ([^\s|\]]+)")

_client: Optional[MossClient] = None
_load_lock = asyncio.Lock()
_index_loaded = False
_timelines: dict = {}
_timelines_at = float("-inf")
_refresh_task: Optional[asyncio.Task] = None


def is_ready() -> bool:
    return _index_loaded


def timelines_cached() -> int:
    return len(_timelines)


def timeline_doc_id(customer_id: str) -> str:
    return f"TIMELINE_{customer_id}"


async def _get_client() -> MossClient:
    """Create the client and pull the index locally once; later queries run in-process."""
    global _client, _index_loaded, _timelines_at, _refresh_task
    async with _load_lock:
        if _client is None:
            _client = MossClient(MOSS_PROJECT_ID, MOSS_PROJECT_KEY)
        if not _index_loaded:
            await _client.load_index(INDEX_NAME, auto_refresh=True, polling_interval_in_seconds=REFRESH_S)
            _index_loaded = True
        if _timelines_at == float("-inf"):
            await _refresh_timelines()
        elif time.monotonic() - _timelines_at > REFRESH_S:
            _timelines_at = time.monotonic()  # claim the refresh; keep serving the stale cache meanwhile
            _refresh_task = asyncio.create_task(_refresh_timelines(background=True))
    return _client


async def _refresh_timelines(background: bool = False):
    """get_docs is a cloud call (~600ms per doc, ~5s for all), so customer timelines are cached in-process."""
    global _timelines, _timelines_at
    try:
        docs = await _client.get_docs(INDEX_NAME)
        _timelines = {d.id: d for d in docs if d.id.startswith("TIMELINE_")}
        _timelines_at = time.monotonic()
    except Exception as e:
        if not background:
            raise
        print(f"[Moss] Timeline refresh failed, keeping cached copy: {e}")


async def warm_up():
    """Load the index and timeline cache before the first call needs them."""
    try:
        await _get_client()
        print(f"[Moss] Index '{INDEX_NAME}' loaded, {len(_timelines)} customer timelines cached.")
    except Exception as e:
        print(f"[Moss] Warm-up failed (will retry on first query): {e}")


def _belongs_to_other_customer(text: str, customer_id: Optional[str]) -> bool:
    """Context leakage prevention: timelines are only visible to their own customer."""
    if "document_type: customer_timeline" not in text:
        return False  # policies, cases and transaction records are shared knowledge
    m = CUSTOMER_ID_RE.search(text)
    return not (customer_id and m and m.group(1) == customer_id)


async def search_context(query: str, top_k: int = 5, customer_id: Optional[str] = None):
    """
    Semantic search over policies/cases plus a direct lookup of the customer's own timeline.
    Returns (results | None on failure, embedding_latency_ms, moss_latency_ms).
    """
    embed_ms = moss_ms = 0.0
    try:
        t0 = time.perf_counter()
        query_embedding = await asyncio.to_thread(get_embedding, query)
        embed_ms = (time.perf_counter() - t0) * 1000

        client = await _get_client()

        async def do_search():
            t1 = time.perf_counter()
            # Over-fetch so leakage filtering doesn't starve the result set
            results = await client.query(INDEX_NAME, query, QueryOptions(top_k=top_k * 3, embedding=query_embedding))
            own = _timelines.get(timeline_doc_id(customer_id)) if customer_id else None
            return results, [own] if own else [], (time.perf_counter() - t1) * 1000

        results, timeline_docs, moss_ms = await asyncio.wait_for(do_search(), timeout=SEARCH_TIMEOUT_S)

        formatted = [{"id": d.id, "text": d.text, "score": None} for d in timeline_docs]
        for doc in results.docs:
            if len(formatted) >= top_k + len(timeline_docs):
                break
            if doc.id in {f["id"] for f in formatted} or _belongs_to_other_customer(doc.text, customer_id):
                continue
            formatted.append({"id": doc.id, "text": doc.text, "score": doc.score})
        return formatted, embed_ms, moss_ms
    except asyncio.TimeoutError:
        print(f"[Moss] Search timed out after {SEARCH_TIMEOUT_S}s; failing safe without context.")
    except Exception as e:
        print(f"[Moss] Search failed: {e}")
    return None, embed_ms, moss_ms
