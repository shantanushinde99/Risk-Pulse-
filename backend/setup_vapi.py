"""
Configure the VAPI assistant: system prompt, first message, server URL and all RiskPulse tools.

    python setup_vapi.py           # back up current config, then apply
    python setup_vapi.py --check   # print the assistant's current tools and server URL

Reads VAPI_API_KEY, VAPI_ASSISTANT_ID, VAPI_SERVER_URL and optional VAPI_WEBHOOK_SECRET from backend/.env.
"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

API_KEY = os.getenv("VAPI_API_KEY")
ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID")
SERVER_URL = os.getenv("VAPI_SERVER_URL", "https://risk-pulse.onrender.com/api/vapi/webhook")
WEBHOOK_SECRET = os.getenv("VAPI_WEBHOOK_SECRET")
BACKUP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vapi_assistant_backup.json")

if not API_KEY or not ASSISTANT_ID:
    sys.exit("Set VAPI_API_KEY and VAPI_ASSISTANT_ID in backend/.env")

URL = f"https://api.vapi.ai/assistant/{ASSISTANT_ID}"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def tool(name, desc, props, required):
    return {
        "type": "function",
        "messages": [{"type": "request-start", "content": "One moment while I check that."}],
        "function": {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


def num(desc):
    return {"type": "number", "description": desc}


def text(desc, enum=None):
    return {"type": "string", "description": desc, **({"enum": enum} if enum else {})}


TOOLS = [
    tool("verify_identity",
         "Verify the caller's identity using their Customer ID. Call this as soon as the customer gives their Customer ID, and before any banking action.",
         {"customer_id": text("The customer's ID exactly as spoken, e.g. C9876543210 or CUST_DEMO_SAFE")},
         ["customer_id"]),
    tool("get_account_summary",
         "Look up the caller's account status and details (account status, how long it has been open, saved payees, registered email). Call this for ANY question about the caller's own account.",
         {},
         []),
    tool("transfer_money",
         "Transfer money to another account. Call this when the customer wants to send money, pay someone, or transfer funds.",
         {"amount": num("The amount to transfer in rupees"),
          "beneficiary_name": text("Name of the person or business receiving the money"),
          "beneficiary_account": text("The recipient's account number or IBAN, if the customer provides it")},
         ["amount", "beneficiary_name"]),
    tool("change_phone_number",
         "Change the customer's registered mobile number.",
         {"new_phone_number": text("The new phone number to register")},
         ["new_phone_number"]),
    tool("change_email",
         "Change the customer's registered email address.",
         {"new_email": text("The new email address to register")},
         ["new_email"]),
    tool("process_refund",
         "Process a refund for a transaction, charge, or payment.",
         {"amount": num("The refund amount in rupees"), "reason": text("The reason for the refund")},
         ["amount"]),
    tool("add_beneficiary",
         "Add a new beneficiary or payee to the customer's account.",
         {"beneficiary_name": text("Name of the new beneficiary"), "account_number": text("The beneficiary's account number")},
         ["beneficiary_name"]),
    tool("reset_pin",
         "Reset the customer's ATM, debit or credit card PIN.",
         {"card_type": text("The card whose PIN should be reset", ["DEBIT", "CREDIT"])},
         ["card_type"]),
    tool("increase_credit_limit",
         "Request a higher credit card limit.",
         {"amount": num("The requested new credit limit in rupees")},
         ["amount"]),
    tool("enable_international_transactions",
         "Enable international transactions on the customer's card, e.g. for travel or overseas purchases.",
         {"card_type": text("The card to enable", ["DEBIT", "CREDIT"])},
         ["card_type"]),
    tool("close_account",
         "Close the customer's bank account.",
         {"reason": text("The reason for closing the account")},
         ["reason"]),
    tool("withdraw_fixed_deposit",
         "Prematurely withdraw (break) a fixed deposit.",
         {"amount": num("The fixed deposit amount to withdraw in rupees"), "fd_id": text("The fixed deposit ID, if provided")},
         ["amount"]),
]

SYSTEM_PROMPT = """You are a professional, friendly and secure AI banking voice agent for RiskPulse Bank.

Every sensitive action MUST go through a tool. The tools decide whether an action is allowed; you never decide that yourself.

RULES:
1. You have NO knowledge of any caller's account. Never state or guess account status, balances, transactions, payees or personal details. The only source of account facts is a tool result in this call.
2. Every caller is unverified until verify_identity succeeds in this call. When the caller gives a Customer ID, call verify_identity immediately with it.
3. Never say an action is done unless a tool result says so. For any banking request or question about the caller's account, call the matching tool. If the tool asks for a Customer ID, ask the caller for it, call verify_identity, then call the original tool again with the same details.
4. If a tool asks the caller to type their registered email on screen, wait until they say they've done it, then call the same tool again with the same details.
5. Read the tool's result to the caller naturally, keeping every fact and reference number. Never add your own conclusions.
6. Never mention risk scores, RiskPulse, confidence levels or internal security systems.
7. Keep replies to 1-3 short sentences. No lists, emojis or markdown.

TOOLS:
- Customer ID given: verify_identity
- Account status or details: get_account_summary
- Send money or pay someone: transfer_money
- Update mobile number: change_phone_number
- Update email address: change_email
- Refund: process_refund
- Add a payee: add_beneficiary
- Forgot or change PIN: reset_pin
- Higher credit limit: increase_credit_limit
- Card abroad or international payments: enable_international_transactions
- Close account: close_account
- Break a fixed deposit: withdraw_fixed_deposit

Only general questions that are not about the caller's own account (e.g. branch hours, what a fixed deposit is) may be answered without tools. If unsure, use a tool."""


def main():
    resp = requests.get(URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    assistant = resp.json()
    model = assistant.get("model", {})

    if "--check" in sys.argv:
        print(f"Assistant: {assistant.get('name')} ({ASSISTANT_ID})")
        print(f"Server URL: {(assistant.get('server') or {}).get('url') or assistant.get('serverUrl')}")
        print(f"Standalone toolIds: {model.get('toolIds') or []}")
        for t in model.get("tools", []):
            print(f"- {t.get('function', {}).get('name')}")
        return

    with open(BACKUP_PATH, "w") as f:
        json.dump(assistant, f, indent=2)
    print(f"Backed up current assistant config to {BACKUP_PATH}")

    model["tools"] = TOOLS
    model["toolIds"] = []  # all tools now live inline; avoids duplicate verify_identity definitions
    model["messages"] = [{"role": "system", "content": SYSTEM_PROMPT}]

    server = {"url": SERVER_URL, "timeoutSeconds": 20}
    if WEBHOOK_SECRET:
        server["headers"] = {"x-vapi-secret": WEBHOOK_SECRET}

    payload = {
        "firstMessage": "Welcome to RiskPulse Bank. To get started, could you please tell me your Customer ID?",
        "model": model,
        "server": server,
    }
    patch = requests.patch(URL, headers=HEADERS, json=payload, timeout=15)
    if patch.status_code != 200:
        sys.exit(f"Update failed ({patch.status_code}): {patch.text}")
    applied = requests.get(URL, headers=HEADERS, timeout=15).json()
    if applied["model"]["messages"][0]["content"] != SYSTEM_PROMPT:
        sys.exit("Update did not stick: the assistant's prompt differs from setup_vapi.py.")
    print(f"Updated assistant with {len(TOOLS)} tools -> {SERVER_URL}")
    print("Note: saving the assistant from an already-open VAPI dashboard tab will overwrite this. Reload the tab first.")


if __name__ == "__main__":
    main()
