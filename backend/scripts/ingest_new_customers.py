"""
Add the custom demo customers (with registered emails) to customers.json/events.json
and push their timeline documents into the live Moss index.
"""
import os
import json
import asyncio
from datetime import datetime, timedelta

from ingest_moss import SYNTHETIC_DIR, INDEX_NAME, MOSS_PROJECT_ID, MOSS_PROJECT_KEY, timeline_document, to_doc_infos
from moss import MossClient

CUSTOMERS_FILE = os.path.join(SYNTHETIC_DIR, "customers.json")
EVENTS_FILE = os.path.join(SYNTHETIC_DIR, "events.json")

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

def merge(path: str, items: list, key: str) -> int:
    with open(path) as f:
        existing = json.load(f)
    ids = {x[key] for x in existing}
    new = [x for x in items if x[key] not in ids]
    if new:
        with open(path, "w") as f:
            json.dump(existing + new, f, indent=2)
    return len(new)


async def main():
    print(f"Customers added: {merge(CUSTOMERS_FILE, NEW_CUSTOMERS, 'customer_id')}")
    print(f"Events added: {merge(EVENTS_FILE, NEW_EVENTS, 'event_id')}")

    with open(EVENTS_FILE) as f:
        events = json.load(f)
    documents = [
        timeline_document(c["customer_id"], [e for e in events if e["customer_id"] == c["customer_id"]])
        for c in NEW_CUSTOMERS
    ]

    client = MossClient(MOSS_PROJECT_ID, MOSS_PROJECT_KEY)
    await client.add_docs(INDEX_NAME, to_doc_infos(documents))
    print(f"Pushed {len(documents)} timeline documents to '{INDEX_NAME}'.")


if __name__ == "__main__":
    asyncio.run(main())
