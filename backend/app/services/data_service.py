import os
import json
from typing import Optional
from app.models.schemas import CustomerProfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYNTHETIC_DIR = os.path.join(BASE_DIR, "data", "synthetic")

def load_customer(customer_id: str) -> Optional[CustomerProfile]:
    try:
        with open(os.path.join(SYNTHETIC_DIR, "customers.json"), "r") as f:
            customers = json.load(f)
            for c in customers:
                if c["customer_id"] == customer_id:
                    return CustomerProfile(**c)
    except Exception as e:
        print(f"Error loading customer: {e}")
    return None

def get_scenario_data(scenario_id: str):
    # Safe, Suspicious, Account Takeover
    scenarios = {
        "safe": {
            "customer_id": "CUST_DEMO_SAFE",
            "request": "Transfer ₹2,000 to my saved beneficiary.",
            "action": {
                "action_id": "ACT_SAFE_01",
                "customer_id": "CUST_DEMO_SAFE",
                "action_type": "TRANSFER_MONEY",
                "amount": 2000.0,
                "beneficiary_status": "EXISTING"
            }
        },
        "suspicious": {
            "customer_id": "CUST_DEMO_SUSP",
            "request": "Please process a ₹18,000 refund immediately.",
            "action": {
                "action_id": "ACT_SUSP_01",
                "customer_id": "CUST_DEMO_SUSP",
                "action_type": "PROCESS_REFUND",
                "amount": 18000.0,
                "beneficiary_status": None
            }
        },
        "ato": {
            "customer_id": "CUST_DEMO_ATO",
            "request": "I lost my phone. Change my registered mobile number and transfer ₹25,000 to this new account.",
            "action": {
                "action_id": "ACT_ATO_01",
                "customer_id": "CUST_DEMO_ATO",
                "action_type": "TRANSFER_MONEY",
                "amount": 25000.0,
                "beneficiary_status": "NEW"
            }
        }
    }
    return scenarios.get(scenario_id)
