import os
import json
import asyncio
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
MOSS_PROJECT_ID = os.getenv("MOSS_PROJECT_ID")
MOSS_PROJECT_KEY = os.getenv("MOSS_PROJECT_KEY") or os.getenv("MOSS_API_KEY")

from moss import MossClient, DocumentInfo

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYNTHETIC_DIR = os.path.join(BASE_DIR, "data", "synthetic")

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
        # Group events by customer to create timelines
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

    print(f"Creating index '{INDEX_NAME}' and adding documents...")
    start_time = time.time()
    try:
        # Note: If MossClient.create_index does not support 'metadata' dict in the list of dicts,
        # we will handle it in the next step. Let's try with metadata first.
        # Ensure we pass the list properly. Some versions might just want id and text.
        
        # Check if index exists or recreate it? The SDK might overwrite or append.
        # For simplicity, we just call create_index which typically creates or replaces.
        # Actually, let's just map to {"id": ..., "text": ...} if metadata fails, 
        # but let's try with metadata included.
        
        # We will format the text to include metadata just in case metadata filtering isn't perfectly supported in the query later,
        # semantic search will still catch it.
        docs_to_ingest = []
        for d in documents:
            meta_str = " | ".join([f"{k}: {v}" for k, v in d.get("metadata", {}).items()])
            text = f"[METADATA: {meta_str}]\n" + d["text"]
            docs_to_ingest.append(DocumentInfo(id=d["id"], text=text))
            
        await client.create_index(INDEX_NAME, docs_to_ingest)
        end_time = time.time()
        print(f"Successfully ingested {len(documents)} documents into '{INDEX_NAME}' in {end_time - start_time:.2f} seconds.")
    except Exception as e:
        print(f"Failed to ingest documents: {e}")

if __name__ == "__main__":
    asyncio.run(ingest())
