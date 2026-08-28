import os
import asyncio
from moss import MossClient, DocumentInfo
from dotenv import load_dotenv

load_dotenv()

MOSS_PROJECT_ID = os.getenv("MOSS_PROJECT_ID")
MOSS_PROJECT_KEY = os.getenv("MOSS_PROJECT_KEY") or os.getenv("MOSS_API_KEY")
INDEX_NAME = "riskpulse-context"

DEMO_EVENTS = [
    {
        "id": "EV_DEMO_SAFE_1",
        "text": "Customer CUST_DEMO_SAFE Historical Case: Normal Beneficiary Transfer Customer has used the same trusted device for over eight months. The beneficiary has received twelve previous transfers. The requested amount is within the customer's norm."
    },
    {
        "id": "EV_DEMO_SAFE_2",
        "text": "Customer CUST_DEMO_SAFE Policy: High-risk transactions should be blocked. Safe transfers under 10k are allowed."
    },
    {
        "id": "EV_DEMO_ATO_1",
        "text": "Customer CUST_DEMO_ATO Customer Timeline events: At 2026-08-21T14:52:28, NEW_DEVICE_LOGIN occurred. At 2026-08-21T19:52:28, NEW_BENEFICIARY occurred. At 2026-08-22T08:15:00, FAILED_OTP occurred. At 2026-08-22T09:12:00, PASSWORD_RESET occurred."
    },
    {
        "id": "EV_DEMO_ATO_2",
        "text": "Customer CUST_DEMO_ATO Historical Case: Account takeover fraud pattern matched."
    },
    {
        "id": "EV_DEMO_SUSP_1",
        "text": "Customer CUST_DEMO_SUSP Customer Timeline events: At 2026-08-27T12:00:00, NEW_DEVICE_LOGIN occurred."
    },
    {
        "id": "EV_DEMO_SUSP_2",
        "text": "Customer CUST_DEMO_SUSP Historical Case: Unusual Refund Request Customer requested a large refund. Amount is unusually high. Similar request pattern flagged for review last month."
    }
]

async def main():
    print("Ingesting context for demo customers into Moss...")
    client = MossClient(MOSS_PROJECT_ID, MOSS_PROJECT_KEY)
    
    await client.load_index(INDEX_NAME)
    
    docs = [DocumentInfo(id=ev["id"], text=ev["text"]) for ev in DEMO_EVENTS]
        
    await client.create_index(INDEX_NAME, docs)
    print(f"Successfully pushed {len(docs)} demo records to Moss.")

if __name__ == "__main__":
    asyncio.run(main())
