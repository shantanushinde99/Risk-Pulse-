import os
import csv
import sys
import json
import asyncio
import time
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
SYNTHETIC_DIR = os.path.join(BASE_DIR, "data", "synthetic")
sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

from moss import MossClient, DocumentInfo
from app.services.embedding_service import get_embeddings_batch
from app.services.moss_service import INDEX_NAME, MOSS_PROJECT_ID, MOSS_PROJECT_KEY, timeline_doc_id


def timeline_document(customer_id: str, events: list) -> dict:
    events = sorted(events, key=lambda x: x["timestamp"])
    text = f"Customer {customer_id} timeline events:\n"
    for e in events:
        text += f"At {e['timestamp']}, {e['event_type']} occurred: {e['details']}\n"
    return {
        "id": timeline_doc_id(customer_id),
        "text": text,
        "metadata": {"document_type": "customer_timeline", "customer_id": customer_id},
    }


def to_doc_infos(documents: list) -> list:
    """Embed documents (metadata is prefixed into the text so it's searchable and filterable)."""
    texts = [
        "[METADATA: " + " | ".join(f"{k}: {v}" for k, v in d["metadata"].items()) + "]\n" + d["text"]
        for d in documents
    ]
    embeddings = get_embeddings_batch(texts, batch_size=10)
    return [DocumentInfo(id=d["id"], text=t, embedding=e) for d, t, e in zip(documents, texts, embeddings)]


async def ingest():
    if not MOSS_PROJECT_ID or not MOSS_PROJECT_KEY:
        print("Error: MOSS_PROJECT_ID and MOSS_PROJECT_KEY must be set in .env")
        return

    print(f"Connecting to Moss with Project ID: {MOSS_PROJECT_ID}")
    client = MossClient(MOSS_PROJECT_ID, MOSS_PROJECT_KEY)

    documents = []

    # 1. Load Policies
    with open(os.path.join(SYNTHETIC_DIR, "policies.json"), "r") as f:
        policies = json.load(f)
        for p in policies:
            doc_id = p["policy_id"]
            text = f"POLICY: {p['name']}\n\n{p['content']}"
            documents.append({
                "id": doc_id,
                "text": text,
                "metadata": {
                    "document_type": "policy",
                    "risk_category": p.get("risk_category"),
                    "severity": p.get("severity")
                }
            })
    
    # 2. Load Historical Cases
    with open(os.path.join(SYNTHETIC_DIR, "historical_cases.json"), "r") as f:
        cases = json.load(f)
        for c in cases:
            doc_id = c["case_id"]
            text = f"CASE: {c['title']}\n\n{c['content']}"
            documents.append({
                "id": doc_id,
                "text": text,
                "metadata": {
                    "document_type": "historical_case",
                    "risk_category": c.get("risk_category"),
                    "severity": c.get("severity")
                }
            })

    # 3. Load Customer Events (one timeline document per customer)
    with open(os.path.join(SYNTHETIC_DIR, "events.json"), "r") as f:
        customer_events = {}
        for e in json.load(f):
            customer_events.setdefault(e["customer_id"], []).append(e)
        for cid, evs in customer_events.items():
            documents.append(timeline_document(cid, evs))

    # 4. Load Bulk PaySim Transactions (to prove scale)
    paysim_path = os.path.join(BASE_DIR, "data", "raw", "paysim.csv")
    print("Loading 1,000 raw transactions from PaySim...")
    try:
        with open(paysim_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                if count >= 1000:
                    break
                
                doc_id = f"PAYSIM_{count}"
                is_fraud = "Yes" if row.get("isFraud", "0") == "1" else "No"
                text = (
                    f"Transaction from {row.get('nameOrig', 'Unknown')} to {row.get('nameDest', 'Unknown')}. "
                    f"Type: {row.get('type', 'Unknown')}. Amount: ${row.get('amount', '0')}. "
                    f"Fraudulent: {is_fraud}."
                )
                
                documents.append({
                    "id": doc_id,
                    "text": text,
                    "metadata": {
                        "document_type": "paysim_transaction",
                        "transaction_type": row.get("type", ""),
                        "is_fraud": is_fraud
                    }
                })
                count += 1
        print(f"Loaded {count} PaySim transactions.")
    except Exception as e:
        print(f"Failed to load PaySim data: {e}")

    print(f"Prepared {len(documents)} documents for ingestion.")

    print("Generating embeddings via Mistral API (this may take a minute)...")
    start_embed = time.time()
    docs_to_ingest = to_doc_infos(documents)
    print(f"Generated {len(docs_to_ingest)} embeddings in {time.time() - start_embed:.2f} seconds.")

    # Step 3: Create the index with model_id="custom"
    print(f"Creating index '{INDEX_NAME}' with custom embeddings...")
    start_time = time.time()
    try:
        await client.create_index(INDEX_NAME, docs_to_ingest, model_id="custom")
        end_time = time.time()
        print(f"Successfully ingested {len(documents)} documents into '{INDEX_NAME}' in {end_time - start_time:.2f} seconds.")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"Index '{INDEX_NAME}' already exists. Deleting and re-creating...")
            await client.delete_index(INDEX_NAME)
            await asyncio.sleep(2)
            await client.create_index(INDEX_NAME, docs_to_ingest, model_id="custom")
            end_time = time.time()
            print(f"Successfully re-ingested {len(documents)} documents into '{INDEX_NAME}' in {end_time - start_time:.2f} seconds.")
        else:
            print(f"Failed to ingest documents: {e}")

if __name__ == "__main__":
    asyncio.run(ingest())
