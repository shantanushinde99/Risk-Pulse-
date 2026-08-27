import pandas as pd
import json
import random
import os
from datetime import datetime, timedelta
from faker import Faker
import uuid

# Configuration
NUMBER_OF_CUSTOMERS = 100
NUMBER_OF_EVENTS = 500
RANDOM_SEED = 42
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAYSIM_PATH = os.path.join(BASE_DIR, "data", "raw", "paysim.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "synthetic")

fake = Faker()
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

def generate_policies():
    policies = [
        {
            "policy_id": "POL_001",
            "name": "ACCOUNT_TAKEOVER_HIGH_RISK",
            "content": "When a password reset and login from a new or untrusted device occur shortly before a high-value financial action, automatic execution must be blocked until additional identity verification is completed.",
            "risk_category": "FRAUD",
            "severity": "CRITICAL"
        },
        {
            "policy_id": "POL_002",
            "name": "NEW_BENEFICIARY_LIMIT",
            "content": "Transfers to a new beneficiary exceeding standard average amounts (e.g. ₹10,000+) must be flagged for VERIFY if accompanied by any unusual device activity.",
            "risk_category": "FRAUD",
            "severity": "HIGH"
        },
        {
            "policy_id": "POL_003",
            "name": "MULTIPLE_FAILED_OTP_LOCKOUT",
            "content": "If an account experiences more than 3 failed OTP attempts within a 15-minute window, any subsequent action changing account details (phone, email) must be blocked.",
            "risk_category": "SECURITY",
            "severity": "CRITICAL"
        },
        {
            "policy_id": "POL_004",
            "name": "SAFE_TRUSTED_DEVICE",
            "content": "Transactions requested from a known trusted device to an existing trusted beneficiary within normal transaction amounts should generally be ALLOWED.",
            "risk_category": "NORMAL",
            "severity": "LOW"
        },
        {
            "policy_id": "POL_005",
            "name": "REFUND_ANOMALY",
            "content": "Refund requests for unusually high amounts relative to account history require VERIFY status, especially if multiple refunds have been requested recently.",
            "risk_category": "FRAUD",
            "severity": "MEDIUM"
        }
    ]
    # We will generate up to 20-30 later, for now starting with core 5.
    for i in range(6, 21):
        policies.append({
            "policy_id": f"POL_{i:03d}",
            "name": f"GENERAL_SECURITY_RULE_{i}",
            "content": fake.sentence(nb_words=15),
            "risk_category": random.choice(["SECURITY", "FRAUD", "COMPLIANCE"]),
            "severity": random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        })
    
    with open(os.path.join(OUTPUT_DIR, "policies.json"), "w") as f:
        json.dump(policies, f, indent=2)

def generate_historical_cases():
    cases = []
    
    # Specific curated cases matching the prompt
    cases.append({
        "case_id": "CASE_FRAUD_042",
        "title": "Account Takeover via Device Change",
        "content": "A customer account was accessed from a new device. The password was reset shortly afterward. Multiple OTP attempts failed before the registered phone number was changed and a new beneficiary was added. A high-value transfer was then requested. Outcome: Confirmed account takeover. Recommended response: BLOCK and require human verification.",
        "risk_category": "ACCOUNT_TAKEOVER",
        "severity": "CRITICAL"
    })
    
    cases.append({
        "case_id": "CASE_SAFE_101",
        "title": "Normal Beneficiary Transfer",
        "content": "Customer has used the same trusted device for over eight months. The beneficiary has received twelve previous transfers. The requested amount is within the customer's normal transaction range. Outcome: Normal transaction. Recommended response: ALLOW.",
        "risk_category": "NORMAL",
        "severity": "LOW"
    })
    
    cases.append({
        "case_id": "CASE_SUSPICIOUS_021",
        "title": "Unusual Refund Request",
        "content": "Customer requested a large refund. Amount is unusually high. Similar request occurred recently. Some unusual account behavior observed without strong confirmation of fraud. Outcome: Potential abuse. Recommended response: VERIFY.",
        "risk_category": "ABUSE",
        "severity": "MEDIUM"
    })
    
    for i in range(4, 51):
        cases.append({
            "case_id": f"CASE_{fake.unique.bothify(text='????_###')}",
            "title": fake.catch_phrase(),
            "content": fake.paragraph(nb_sentences=3),
            "risk_category": random.choice(["ACCOUNT_TAKEOVER", "SCAM", "MONEY_LAUNDERING", "NORMAL", "ABUSE"]),
            "severity": random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        })

    with open(os.path.join(OUTPUT_DIR, "historical_cases.json"), "w") as f:
        json.dump(cases, f, indent=2)

def generate_customers_and_events():
    customers = []
    events = []
    
    # We will sample from PaySim if it exists, otherwise fallback to fully synthetic
    try:
        df = pd.read_csv(PAYSIM_PATH, nrows=5000)
        unique_senders = df['nameOrig'].unique().tolist()
        customer_ids = unique_senders[:NUMBER_OF_CUSTOMERS]
    except Exception as e:
        print(f"Could not load PaySim data: {e}. Using fully synthetic IDs.")
        customer_ids = [f"CUST_{i:04d}" for i in range(NUMBER_OF_CUSTOMERS)]

    # Make sure we have our demo customers
    demo_customers = ["CUST_DEMO_SAFE", "CUST_DEMO_SUSP", "CUST_DEMO_ATO"]
    customer_ids.extend(demo_customers)

    for cid in customer_ids:
        # Create profile
        profile = {
            "customer_id": cid,
            "account_age": random.randint(30, 3650),
            "average_transaction_amount": round(random.uniform(500, 10000), 2),
            "transaction_frequency": random.randint(1, 30),
            "known_devices": [fake.uuid4() for _ in range(random.randint(1, 3))],
            "trusted_beneficiaries": [fake.iban() for _ in range(random.randint(1, 5))],
            "baseline_risk": random.randint(0, 30) if "DEMO" not in cid else (0 if "SAFE" in cid else 20)
        }
        customers.append(profile)

        # Generate coherent events based on customer type
        num_events = random.randint(2, 10)
        base_time = datetime.now() - timedelta(days=random.randint(1, 30))
        
        if cid == "CUST_DEMO_ATO":
            # Account Takeover pattern
            events.extend([
                {"event_id": str(uuid.uuid4()), "customer_id": cid, "timestamp": (base_time).isoformat(), "event_type": "NEW_DEVICE_LOGIN", "severity": "HIGH", "details": "Login from unrecognized device in new location."},
                {"event_id": str(uuid.uuid4()), "customer_id": cid, "timestamp": (base_time + timedelta(minutes=2)).isoformat(), "event_type": "PASSWORD_RESET", "severity": "HIGH", "details": "Password reset successfully via email link."},
                {"event_id": str(uuid.uuid4()), "customer_id": cid, "timestamp": (base_time + timedelta(minutes=4)).isoformat(), "event_type": "FAILED_OTP", "severity": "MEDIUM", "details": "Failed OTP verification."},
                {"event_id": str(uuid.uuid4()), "customer_id": cid, "timestamp": (base_time + timedelta(minutes=5)).isoformat(), "event_type": "FAILED_OTP", "severity": "MEDIUM", "details": "Failed OTP verification."},
                {"event_id": str(uuid.uuid4()), "customer_id": cid, "timestamp": (base_time + timedelta(minutes=8)).isoformat(), "event_type": "NEW_BENEFICIARY", "severity": "HIGH", "details": "New beneficiary added to account."}
            ])
        elif cid == "CUST_DEMO_SAFE":
            events.extend([
                {"event_id": str(uuid.uuid4()), "customer_id": cid, "timestamp": (base_time).isoformat(), "event_type": "KNOWN_DEVICE_LOGIN", "severity": "LOW", "details": "Login from recognized trusted device."},
                {"event_id": str(uuid.uuid4()), "customer_id": cid, "timestamp": (base_time + timedelta(days=2)).isoformat(), "event_type": "IDENTITY_VERIFIED", "severity": "LOW", "details": "Biometric identity verified successfully."}
            ])
        elif cid == "CUST_DEMO_SUSP":
            events.extend([
                {"event_id": str(uuid.uuid4()), "customer_id": cid, "timestamp": (base_time).isoformat(), "event_type": "KNOWN_DEVICE_LOGIN", "severity": "LOW", "details": "Login from recognized trusted device."},
                {"event_id": str(uuid.uuid4()), "customer_id": cid, "timestamp": (base_time + timedelta(days=1)).isoformat(), "event_type": "SUSPICIOUS_LOCATION_CHANGE", "severity": "MEDIUM", "details": "IP address indicates location change within short timeframe."}
            ])
        else:
            # Random events
            event_types = ["KNOWN_DEVICE_LOGIN", "NEW_DEVICE_LOGIN", "PASSWORD_RESET", "FAILED_OTP", "NEW_BENEFICIARY", "PHONE_CHANGE_REQUEST", "IDENTITY_VERIFIED"]
            for j in range(num_events):
                events.append({
                    "event_id": str(uuid.uuid4()),
                    "customer_id": cid,
                    "timestamp": (base_time + timedelta(hours=j*5)).isoformat(),
                    "event_type": random.choice(event_types),
                    "severity": random.choice(["LOW", "MEDIUM", "HIGH"]),
                    "details": fake.sentence()
                })

    with open(os.path.join(OUTPUT_DIR, "customers.json"), "w") as f:
        json.dump(customers, f, indent=2)
        
    with open(os.path.join(OUTPUT_DIR, "events.json"), "w") as f:
        json.dump(events, f, indent=2)

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Generating synthetic data...")
    generate_policies()
    generate_historical_cases()
    generate_customers_and_events()
    print("Synthetic data generation complete.")
