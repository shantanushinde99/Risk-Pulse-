import os
import json
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# We need the MossClient
from moss import MossClient, MutationOptions, DocumentInfo

MOSS_PROJECT_ID = os.getenv("MOSS_PROJECT_ID")
MOSS_PROJECT_KEY = os.getenv("MOSS_PROJECT_KEY") or os.getenv("MOSS_API_KEY")
INDEX_NAME = "riskpulse-context"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNTHETIC_DIR = os.path.join(BASE_DIR, "data", "synthetic")
CUSTOMERS_FILE = os.path.join(SYNTHETIC_DIR, "customers.json")

NEW_CUSTOMERS = [
    {
        "customer_id": "C9876543210",
        "name": "Shantanu Shinde",
        "email": "shantanushinde2433@gmail.com",
        "account_age": 1400,
        "average_transaction_amount": 5000.0,
        "transaction_frequency": 12,
        "known_devices": ["device_shantanu_1", "device_shantanu_2"],
        "trusted_beneficiaries": ["BENEF_1", "BENEF_2"],
        "baseline_risk": 15
    },
    {
        "customer_id": "C1234567890",
        "name": "MT",
        "email": "mt6505094@gmail.com",
        "account_age": 850,
        "average_transaction_amount": 12000.0,
        "transaction_frequency": 30,
        "known_devices": ["device_mt_1"],
        "trusted_beneficiaries": ["BENEF_3"],
        "baseline_risk": 18
    }
]

# Create some recent synthetic security events for context retrieval
NEW_EVENTS = [
    {
        "event_id": "EV_SH_1",
        "customer_id": "C9876543210",
        "timestamp": (datetime.now() - timedelta(days=2)).isoformat(),
        "event_type": "DEVICE_ADDED",
        "severity": "LOW",
        "details": "Customer successfully added and verified a new trusted device (device_shantanu_2) via 2FA.",
        "metadata": {}
    },
    {
        "event_id": "EV_SH_2",
        "customer_id": "C9876543210",
        "timestamp": (datetime.now() - timedelta(hours=5)).isoformat(),
        "event_type": "LARGE_DEPOSIT",
        "severity": "LOW",
        "details": "Customer received a scheduled salary deposit. Behavioral profile remains stable.",
        "metadata": {}
    },
    {
        "event_id": "EV_MT_1",
        "customer_id": "C1234567890",
        "timestamp": (datetime.now() - timedelta(days=7)).isoformat(),
        "event_type": "PASSWORD_RESET",
        "severity": "MEDIUM",
        "details": "Customer successfully reset their password following a routine security check.",
        "metadata": {}
    },
    {
        "event_id": "EV_MT_2",
        "customer_id": "C1234567890",
        "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
        "event_type": "FAILED_LOGIN",
        "severity": "LOW",
        "details": "Failed login attempt detected from an unrecognized IP, but subsequent login was successful from a known device (device_mt_1).",
        "metadata": {}
    }
]

async def main():
    print("1. Updating customers.json with 2 new customers...")
    
    with open(CUSTOMERS_FILE, "r") as f:
        customers = json.load(f)
        
    # Prevent duplication if script is run multiple times
    existing_ids = {c["customer_id"] for c in customers}
    added_count = 0
    for nc in NEW_CUSTOMERS:
        if nc["customer_id"] not in existing_ids:
            customers.append(nc)
            added_count += 1
            
    if added_count > 0:
        with open(CUSTOMERS_FILE, "w") as f:
            json.dump(customers, f, indent=2)
        print(f"Added {added_count} new customers.")
    else:
        print("Customers already exist in customers.json. Skipping append.")
        
    print("\n2. Ingesting their specific behavioral context into Moss...")
    client = MossClient(MOSS_PROJECT_ID, MOSS_PROJECT_KEY)
    
    # We will just append to the existing index
    await client.load_index(INDEX_NAME)
    
    docs_to_ingest = []
    for ev in NEW_EVENTS:
        doc = DocumentInfo(
            id=ev["event_id"],
            text=f"Customer {ev['customer_id']} behavior log: {ev['event_type']} - {ev['details']}. Severity: {ev['severity']}. Date: {ev['timestamp']}"
        )
        docs_to_ingest.append(doc)
        
    print(f"Pushing {len(docs_to_ingest)} records to Moss...")
    await client.add_docs(INDEX_NAME, docs_to_ingest)
    print("Ingestion complete! The risk engine will now have full context for C9876543210 and C1234567890.")

if __name__ == "__main__":
    asyncio.run(main())
