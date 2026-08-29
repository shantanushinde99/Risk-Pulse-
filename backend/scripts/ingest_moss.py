import os
import json
import asyncio
import time
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
MOSS_PROJECT_ID = os.getenv("MOSS_PROJECT_ID")
MOSS_PROJECT_KEY = os.getenv("MOSS_PROJECT_KEY") or os.getenv("MOSS_API_KEY")

from moss import MossClient, DocumentInfo

# Add parent to path so we can import our embedding service
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.services.embedding_service import get_embeddings_batch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYNTHETIC_DIR = os.path.join(BASE_DIR, "data", "synthetic")

# Fallback: check inside backend/data/synthetic if the above doesn't exist
if not os.path.exists(SYNTHETIC_DIR):
    SYNTHETIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "synthetic")

INDEX_NAME = "riskpulse-context"

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

    # 3. Load Customer Events (Customer Timeline)
    with open(os.path.join(SYNTHETIC_DIR, "events.json"), "r") as f:
        events = json.load(f)
        customer_events = {}
        for e in events:
            cid = e["customer_id"]
            if cid not in customer_events:
                customer_events[cid] = []
            customer_events[cid].append(e)

        for cid, evs in customer_events.items():
            evs.sort(key=lambda x: x["timestamp"])
            timeline_text = f"Customer {cid} timeline events:\n"
            for e in evs:
                timeline_text += f"At {e['timestamp']}, {e['event_type']} occurred: {e['details']}\n"
            
            documents.append({
                "id": f"TIMELINE_{cid}",
                "text": timeline_text,
                "metadata": {
                    "document_type": "customer_timeline",
                    "customer_id": cid
                }
            })

    # 4. Load Bulk PaySim Transactions (to prove scale)
    import csv
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

    # Step 1: Generate embeddings for all documents using Mistral
    print("Generating embeddings via Mistral API (this may take a minute)...")
    start_embed = time.time()
    
    texts_to_embed = []
    for d in documents:
        meta_str = " | ".join([f"{k}: {v}" for k, v in d.get("metadata", {}).items()])
        text = f"[METADATA: {meta_str}]\n" + d["text"]
        texts_to_embed.append(text)
    
    embeddings = get_embeddings_batch(texts_to_embed, batch_size=10)
    embed_time = time.time() - start_embed
    print(f"Generated {len(embeddings)} embeddings in {embed_time:.2f} seconds.")

    # Step 2: Create DocumentInfo objects with custom embeddings
    docs_to_ingest = []
    for i, d in enumerate(documents):
        meta_str = " | ".join([f"{k}: {v}" for k, v in d.get("metadata", {}).items()])
        text = f"[METADATA: {meta_str}]\n" + d["text"]
        docs_to_ingest.append(DocumentInfo(id=d["id"], text=text, embedding=embeddings[i]))

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
