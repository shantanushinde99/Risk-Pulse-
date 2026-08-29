import os
import time
import asyncio
from moss import MossClient, QueryOptions
from dotenv import load_dotenv
from app.services.embedding_service import get_embedding

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))

MOSS_PROJECT_ID = os.getenv("MOSS_PROJECT_ID")
MOSS_PROJECT_KEY = os.getenv("MOSS_PROJECT_KEY") or os.getenv("MOSS_API_KEY")
INDEX_NAME = "riskpulse-context"

client = None

def get_moss_client():
    global client
    if client is None:
        client = MossClient(MOSS_PROJECT_ID, MOSS_PROJECT_KEY)
    return client

async def search_context(query: str, top_k: int = 5, customer_id: str = None) -> tuple[list[dict], float]:
    """
    Search Moss index for contextual documents using custom embeddings.
    Returns a tuple of (results, latency_ms)
    """
    start_time = time.perf_counter()
    
    try:
        c = get_moss_client()
        
        # Generate query embedding using Mistral
        query_embedding = get_embedding(query)
        
        async def do_search():
            await c.load_index(INDEX_NAME)
            # Pass the custom embedding vector to Moss query
            return await c.query(
                INDEX_NAME, 
                query, 
                QueryOptions(top_k=top_k, embedding=query_embedding)
            )
            
        # Hard timeout of 8 seconds to ensure VAPI webhooks never fail
        results = await asyncio.wait_for(do_search(), timeout=8.0)
        
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        
        formatted_results = []
        for doc in results.docs:
            # Prevent context leakage: Only accept documents that belong to this customer
            if customer_id and customer_id not in doc.text:
                continue
                
            formatted_results.append({
                "id": doc.id,
                "text": doc.text,
                "score": doc.score
            })
            
        return formatted_results, latency_ms
    except asyncio.TimeoutError:
        print(f"Moss search timed out after 8 seconds, bypassing semantic context to prevent VAPI crash.")
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        return [], latency_ms
    except Exception as e:
        print(f"Moss search failed: {e}")
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        return [], latency_ms
