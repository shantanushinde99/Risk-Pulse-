import requests
import json

API_KEY = "79b1fc90-5245-4007-8f14-7ee86de5d03f"
ASSISTANT_ID = "e6f879b5-b9e5-403a-831a-64500dda7057"
SERVER_URL = "https://imprudent-tranquil-precise.ngrok-free.dev/api/vapi/webhook"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def make_tool(name, desc, props, required):
    return {
        "type": "function",
        "messages": [
            {
                "type": "request-start",
                "content": "Let me check that for you."
            },
            {
                "type": "request-complete",
                "content": ""
            }
        ],
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required
            }
        },
        "server": {
            "url": SERVER_URL
        }
    }

tools = [
    make_tool(
        "transfer_money",
        "Transfer money from the customer's account to another account. Always call this when the customer wants to send money, make a payment, or transfer funds.",
        {
            "amount": {"type": "number", "description": "The amount to transfer in rupees"},
            "beneficiary_status": {"type": "string", "description": "Whether the recipient is a NEW or EXISTING beneficiary", "enum": ["NEW", "EXISTING"]}
        },
        ["amount", "beneficiary_status"]
    ),
    make_tool(
        "change_phone_number",
        "Change the customer's registered mobile phone number on their account. Call this when a customer wants to update their phone number.",
        {
            "new_phone_number": {"type": "string", "description": "The new phone number the customer wants to register"}
        },
        ["new_phone_number"]
    ),
    make_tool(
        "change_email",
        "Change the customer's registered email address on their account. Call this when a customer wants to update their email.",
        {
            "new_email": {"type": "string", "description": "The new email address the customer wants to register"}
        },
        ["new_email"]
    ),
    make_tool(
        "process_refund",
        "Process a refund for the customer. Call this when the customer requests a refund for a transaction, charge, or payment.",
        {
            "amount": {"type": "number", "description": "The refund amount in rupees"},
            "reason": {"type": "string", "description": "The reason for the refund"}
        },
        ["amount"]
    ),
    make_tool(
        "add_beneficiary",
        "Add a new beneficiary or payee to the customer's account. Call this when a customer wants to add someone as a new payment recipient.",
        {
            "beneficiary_name": {"type": "string", "description": "The name of the new beneficiary"},
            "account_number": {"type": "string", "description": "The beneficiary's account number"}
        },
        ["beneficiary_name"]
    ),
    make_tool(
        "reset_pin",
        "Reset the customer's ATM or debit card PIN. Call this when a customer has forgotten their PIN or wants to change it.",
        {
            "card_type": {"type": "string", "description": "The type of card to reset PIN for", "enum": ["DEBIT", "CREDIT"]}
        },
        ["card_type"]
    ),
    make_tool(
        "increase_credit_limit",
        "Request an increase in the customer's credit card spending limit. Call this when a customer wants a higher credit limit.",
        {
            "amount": {"type": "number", "description": "The requested new credit limit amount in rupees"}
        },
        ["amount"]
    ),
    make_tool(
        "enable_international_transactions",
        "Enable international transactions on the customer's debit or credit card. Call this when a customer wants to use their card for overseas purchases or ATM withdrawals abroad.",
        {
            "card_type": {"type": "string", "description": "The type of card to enable international transactions on", "enum": ["DEBIT", "CREDIT"]}
        },
        ["card_type"]
    ),
    make_tool(
        "close_account",
        "Close the customer's bank account. Call this when a customer requests to close or terminate their account.",
        {
            "reason": {"type": "string", "description": "The reason for closing the account"}
        },
        ["reason"]
    ),
    make_tool(
        "withdraw_fixed_deposit",
        "Withdraw or break a fixed deposit before its maturity date. Call this when a customer wants to prematurely close their FD and withdraw the funds.",
        {
            "amount": {"type": "number", "description": "The fixed deposit amount to withdraw in rupees"},
            "fd_id": {"type": "string", "description": "The fixed deposit ID or reference number if the customer provides it"}
        },
        ["amount"]
    )
]

url = f"https://api.vapi.ai/assistant/{ASSISTANT_ID}"
print(f"Fetching VAPI Assistant {ASSISTANT_ID}...")

# First GET the assistant to preserve the existing model configuration (provider, model name, etc)
get_resp = requests.get(url, headers=headers)
if get_resp.status_code != 200:
    print(f"Failed to fetch assistant: {get_resp.text}")
    exit(1)

assistant = get_resp.json()
model_obj = assistant.get("model", {})

# Update the tools array
model_obj["tools"] = tools

# Update the system prompt
system_prompt = """You are a professional, highly secure AI banking agent for RiskPulse Bank. You assist customers over the phone with their banking needs. 

You have access to a suite of security-hardened tools. RiskPulse is our zero-latency contextual risk and safety layer. EVERY sensitive action you take MUST be routed through RiskPulse by calling the appropriate tool. 

CRITICAL RULES:
1. NEVER confirm or execute an action without calling a tool first.
2. If a customer asks to perform any of the actions below, you MUST immediately call the corresponding tool.
3. Once the tool returns a result, you MUST read the EXACT response provided by the tool back to the customer naturally. Do not paraphrase it or add your own conclusions.

TOOL MAPPING GUIDE:
- If customer wants to send money or make a payment: CALL `transfer_money`
- If customer wants to update their mobile number: CALL `change_phone_number`
- If customer wants to update their email address: CALL `change_email`
- If customer wants a refund for a transaction: CALL `process_refund`
- If customer wants to add a new payee/beneficiary: CALL `add_beneficiary`
- If customer forgot their PIN or wants to reset it: CALL `reset_pin`
- If customer asks for a higher credit limit: CALL `increase_credit_limit`
- If customer is traveling and needs international transactions on: CALL `enable_international_transactions`
- If customer wants to close their bank account: CALL `close_account`
- If customer wants to prematurely break a fixed deposit: CALL `withdraw_fixed_deposit`

If the customer is just asking general questions, you can answer them conversationally. But for any action listed above, ALWAYS trigger the tool."""

model_obj["messages"] = [
    {
        "role": "system",
        "content": system_prompt
    }
]

payload = {
    "firstMessage": "Welcome to RiskPulse Bank. How can I help you today?",
    "model": model_obj
}

print(f"Updating VAPI Assistant {ASSISTANT_ID} with 10 tools and new prompts...")
response = requests.patch(url, headers=headers, json=payload)

if response.status_code == 200:
    print("Successfully updated VAPI Assistant tools!")
else:
    print(f"Failed: {response.status_code}")
    print(response.text)
