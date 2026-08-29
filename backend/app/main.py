import time
import random
import string
import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.models.schemas import ScenarioResponse, AgentAction, CustomerProfile
from app.services.data_service import get_scenario_data, load_customer
from app.services.moss_service import search_context
from app.services.risk_engine import evaluate_risk
from app.services.agent_service import generate_agent_response
from app.services.email_service import send_confirmation_email
app = FastAPI(title="RiskPulse API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# State
# ─────────────────────────────────────────────

# Store recent events for the frontend UI
recent_vapi_evaluations = []

# Session state: stores the verified customer_id after identity verification
# In production, this would be per-session (e.g., keyed by VAPI call ID)
verified_customer_id: Optional[str] = None


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok"}


# ─────────────────────────────────────────────
# Scenario Endpoints (Dashboard Demo)
# ─────────────────────────────────────────────

@app.get("/api/scenarios")
def list_scenarios():
    return {
        "scenarios": [
            {"id": "safe", "name": "Safe Transaction"},
            {"id": "suspicious", "name": "Suspicious Request"},
            {"id": "ato", "name": "Account Takeover"}
        ]
    }

@app.post("/api/scenarios/{scenario_id}/run", response_model=ScenarioResponse)
async def run_scenario(scenario_id: str):
    start_total = time.perf_counter()
    
    # 1. Load Scenario Data
    scenario = get_scenario_data(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
        
    action_data = scenario["action"]
    customer_id = action_data["customer_id"]
    customer_request = scenario["request"]
    
    # 2. Parse Action and Customer
    action = AgentAction(**action_data)
    customer = load_customer(customer_id)
    if not customer:
        # Fallback empty profile for resilience
        customer = CustomerProfile(
            customer_id=customer_id, 
            account_age=365, 
            average_transaction_amount=1000, 
            transaction_frequency=10, 
            known_devices=[], 
            trusted_beneficiaries=[], 
            baseline_risk=10
        )
        
    # 3. Retrieve Context from Moss
    # We formulate a query based on the action and customer
    query = f"Evaluate risk for {action.action_type} of {action.amount}. Customer baseline risk {customer.baseline_risk}."
    if action.beneficiary_status == "NEW":
        query += " New beneficiary added."
    if action.action_type in ["CHANGE_PHONE", "CHANGE_EMAIL"]:
        query += " Account details changed."
        
    start_backend = time.perf_counter()
    context_items, moss_latency_ms = await search_context(query, top_k=5, customer_id=customer_id)
    
    # 4. Evaluate Risk
    risk_decision, eval_latency_ms = evaluate_risk(action, customer, context_items)
    
    end_backend = time.perf_counter()
    backend_latency_ms = (end_backend - start_backend) * 1000
    total_guardrail_latency = moss_latency_ms + backend_latency_ms
    
    # 5. Generate LLM Response
    final_response, llm_latency_ms = generate_agent_response(customer_request, risk_decision)
    
    end_total = time.perf_counter()
    
    return ScenarioResponse(
        customer_request=customer_request,
        action=action,
        moss_latency_ms=round(moss_latency_ms, 2),
        backend_latency_ms=round(backend_latency_ms, 2),
        risk_evaluation_latency_ms=round(eval_latency_ms, 2),
        total_guardrail_latency_ms=round(total_guardrail_latency, 2),
        llm_latency_ms=round(llm_latency_ms, 2),
        decision=risk_decision,
        final_response=final_response
    )


# ─────────────────────────────────────────────
# Custom Evaluation Endpoint (Sandbox)
# ─────────────────────────────────────────────

class CustomEvaluationRequest(BaseModel):
    action_type: str
    amount: float
    beneficiary_status: str
    baseline_risk: int

@app.post("/api/evaluate-custom", response_model=ScenarioResponse)
async def evaluate_custom(req: CustomEvaluationRequest):
    start_total = time.perf_counter()
    
    action = AgentAction(
        action_id="CUSTOM_123",
        customer_id="CUST_CUSTOM",
        action_type=req.action_type,
        amount=req.amount,
        beneficiary_status=req.beneficiary_status,
    )
    
    customer = CustomerProfile(
        customer_id="CUST_CUSTOM",
        account_age=365,
        average_transaction_amount=1000,
        transaction_frequency=10,
        known_devices=[],
        trusted_beneficiaries=[],
        baseline_risk=req.baseline_risk
    )
    
    query = f"Evaluate risk for {action.action_type} of {action.amount}. Customer baseline risk {customer.baseline_risk}."
    if action.beneficiary_status == "NEW":
        query += " New beneficiary added."
    if action.action_type in ["CHANGE_PHONE", "CHANGE_EMAIL"]:
        query += " Account details changed."
        
    start_backend = time.perf_counter()
    context_items, moss_latency_ms = await search_context(query, top_k=5, customer_id=customer.customer_id)
    
    risk_decision, eval_latency_ms = evaluate_risk(action, customer, context_items)
    
    end_backend = time.perf_counter()
    backend_latency_ms = (end_backend - start_backend) * 1000
    total_guardrail_latency = moss_latency_ms + backend_latency_ms
    
    final_response, llm_latency_ms = generate_agent_response("Custom request via Sandbox", risk_decision)
    
    return ScenarioResponse(
        customer_request="Custom Request",
        action=action,
        moss_latency_ms=round(moss_latency_ms, 2),
        backend_latency_ms=round(backend_latency_ms, 2),
        risk_evaluation_latency_ms=round(eval_latency_ms, 2),
        total_guardrail_latency_ms=round(total_guardrail_latency, 2),
        llm_latency_ms=round(llm_latency_ms, 2),
        decision=risk_decision,
        final_response=final_response
    )


# ─────────────────────────────────────────────
# Analytics Endpoint (Dashboard)
# ─────────────────────────────────────────────

@app.get("/api/analytics")
def get_analytics():
    # Return analytics data for the dashboard
    return {
        "total_evaluated": 1542,
        "allow_count": 1205,
        "verify_count": 210,
        "block_count": 89,
        "escalate_count": 38,
        "avg_moss_latency_ms": 7.4,
        "avg_guardrail_latency_ms": 15.3,
        "recent_high_risk": [
            {"id": "EVT_102", "type": "TRANSFER_MONEY", "score": 94, "decision": "BLOCK"},
            {"id": "EVT_099", "type": "CHANGE_PHONE", "score": 88, "decision": "BLOCK"}
        ]
    }


# ─────────────────────────────────────────────
# VAPI Voice Agent Webhook — Multi-Tool Dispatcher
# All tools run through the RiskPulse guardrail
# ─────────────────────────────────────────────

# Maps VAPI tool names → action_type for the Risk Engine
TOOL_ACTION_MAP = {
    "transfer_money": "TRANSFER_MONEY",
    "change_phone_number": "CHANGE_PHONE",
    "change_email": "CHANGE_EMAIL",
    "process_refund": "PROCESS_REFUND",
    "add_beneficiary": "ADD_BENEFICIARY",
    "reset_pin": "RESET_PIN",
    "increase_credit_limit": "INCREASE_CREDIT_LIMIT",
    "enable_international_transactions": "ENABLE_INTL_TXN",
    "close_account": "CLOSE_ACCOUNT",
    "withdraw_fixed_deposit": "WITHDRAW_FD",
    "verify_identity": "VERIFY_IDENTITY",
}


def _build_moss_query(action_type: str, amount: float, args: dict) -> str:
    """Build a rich semantic query for Moss based on the tool being called."""
    queries = {
        "TRANSFER_MONEY": f"Risk assessment for money transfer of {amount}. Check for fraud patterns, suspicious beneficiary, and velocity limits.",
        "CHANGE_PHONE": "Customer requesting phone number change. Check for account takeover patterns, recent suspicious activity, and identity verification policies.",
        "CHANGE_EMAIL": "Customer requesting email address change. Check for account takeover patterns and credential change policies.",
        "PROCESS_REFUND": f"Customer requesting refund of {amount}. Check for refund abuse patterns and refund fraud policies.",
        "ADD_BENEFICIARY": f"Customer adding a new beneficiary. Check for social engineering patterns, mule account indicators, and beneficiary policies.",
        "RESET_PIN": "Customer requesting PIN reset via voice channel. Check for unauthorized access attempts and PIN reset policies.",
        "INCREASE_CREDIT_LIMIT": f"Customer requesting credit limit increase to {amount}. Check for credit fraud patterns and eligibility policies.",
        "ENABLE_INTL_TXN": "Customer requesting to enable international transactions. Check for card cloning, cross-border fraud patterns, and international transaction policies.",
        "CLOSE_ACCOUNT": "Customer requesting account closure via voice. Check for coerced closure patterns, elder abuse indicators, and account closure policies.",
        "WITHDRAW_FD": f"Customer requesting premature fixed deposit withdrawal of {amount}. Check for coerced withdrawal patterns and FD withdrawal policies.",
        "VERIFY_IDENTITY": f"Analyze behavioral risk and historical transaction patterns for customer {args.get('customer_id', '')}. Check for suspicious activity or high risk baseline.",
    }
    return queries.get(action_type, f"Evaluate risk for {action_type} of amount {amount}.")


def _build_spoken_response(action_type: str, decision: str, risk_score: int, explanation: str, amount: float) -> str:
    """Build a natural, tool-specific spoken response based on the RiskPulse decision."""
    ref_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    # Tool-specific language for each decision
    tool_labels = {
        "TRANSFER_MONEY": "transfer",
        "CHANGE_PHONE": "phone number change",
        "CHANGE_EMAIL": "email address change",
        "PROCESS_REFUND": "refund",
        "ADD_BENEFICIARY": "new beneficiary addition",
        "RESET_PIN": "PIN reset",
        "INCREASE_CREDIT_LIMIT": "credit limit increase",
        "ENABLE_INTL_TXN": "international transaction enablement",
        "CLOSE_ACCOUNT": "account closure",
        "WITHDRAW_FD": "fixed deposit withdrawal",
    }
    action_label = tool_labels.get(action_type, "request")

    if action_type == "VERIFY_IDENTITY":
        if decision == "BLOCK":
            return (
                f"After reviewing your account history, our security system detected highly suspicious activity patterns. "
                f"I am unable to authenticate you or process any requests at this time. "
                f"Please visit your nearest branch with a valid photo ID. Your reference number is {ref_id}."
            )
        else:
            return "Thank you. I have successfully verified your identity. Please immediately proceed with executing the original request now."

    if decision == "BLOCK":
        return (
            f"I'm sorry, but I can't process a {action_label} right now. "
            f"Because we aren't able to fully verify your identity at the moment, we can't proceed with this action for your security. "
            f"Please visit your nearest branch with a valid photo ID, or contact our support team. "
            f"Your reference number is {ref_id}."
        )
    elif decision == "VERIFY":
        return (
            f"I'd be happy to help with this {action_label}. "
            f"For your security, I just need to quickly verify your identity first. "
            f"Please type your Customer ID into the chat box below to proceed."
        )
    elif decision == "ESCALATE":
        return (
            f"I think it's best if a specialist handles this {action_label} for you. "
            f"Let me quickly connect you to a human agent who can assist you further. "
            f"Please hold. Your reference number is {ref_id}."
        )
    else:  # ALLOW
        # Format with commas so the text-to-speech engine reads it perfectly
        amt_text = f" of {int(amount):,} rupees" if amount and amount > 0 else ""
        return (
            f"I've gone ahead and processed your {action_label}{amt_text} successfully. "
            f"Your confirmation number is {ref_id}. "
            f"Is there anything else I can help you with today?"
        )


# ─────────────────────────────────────────────
# VAPI Endpoints
# ─────────────────────────────────────────────



@app.get("/api/vapi/latest-evaluations")
def get_latest_vapi_evaluations():
    return {"evaluations": recent_vapi_evaluations[-10:]}

@app.post("/api/vapi/reset")
def reset_vapi_state():
    global demo_auth_email
    recent_vapi_evaluations.clear()
    verified_calls.clear()
    demo_auth_email = ""
    return {"status": "ok", "message": "State reset successfully"}

# Store recent events for the frontend UI
recent_vapi_evaluations = []

# Store verified customer IDs per call to prevent state leaking across different phone calls!
verified_calls = {}

# Email typed by the user in the frontend for authentication
demo_auth_email = ""

# Pending email confirmation: stores the last ALLOWED transaction so we can
# send the confirmation email only after the user types their registered email.
pending_email_confirmation = {}

@app.post("/api/vapi/set-auth-email")
async def set_auth_email(request: Request):
    global demo_auth_email, pending_email_confirmation
    body = await request.json()
    demo_auth_email = body.get("email", "").strip().lower()
    print(f"[Auth] Frontend auth email set to: {demo_auth_email}")

    # If there is a pending confirmation, verify the email now
    if pending_email_confirmation and demo_auth_email:
        registered = pending_email_confirmation.get("registered_email", "").strip().lower()
        if demo_auth_email == registered:
            # Email matches! Send the confirmation email.
            send_confirmation_email(
                pending_email_confirmation["customer_email"],
                pending_email_confirmation["action_type"],
                pending_email_confirmation["amount"]
            )
            result = {"status": "ok", "verified": True, "message": "Email verified. Confirmation sent!"}
            pending_email_confirmation = {}  # Clear after sending
            return result
        else:
            print(f"[Auth] Email mismatch: '{demo_auth_email}' != '{registered}'")
            return {"status": "blocked", "verified": False, "message": "Email does not match registered account."}

    return {"status": "ok", "email": demo_auth_email}

@app.post("/api/vapi/webhook")
async def vapi_webhook(request: Request):
    """
    Multi-tool webhook for VAPI voice agent.
    Every tool runs through the full RiskPulse pipeline:
    Moss semantic retrieval → Deterministic Risk Engine → Decision.
    """
    global verified_calls, pending_email_confirmation
    
    payload = await request.json()
    message = payload.get("message", {})
    call_obj = message.get("call", {})
    call_id = call_obj.get("id", "unknown_call")

    # Only process tool-calls messages
    if message.get("type") != "tool-calls":
        return {"results": []}

    tool_calls = message.get("toolCalls", [])
    if not tool_calls:
        return {"results": []}

    results = []
    for tc in tool_calls:
        tool_call_id = tc.get("id", "")
        fn = tc.get("function", {})
        fn_name = fn.get("name", "")
        args = fn.get("arguments", {})

        print(f"[VAPI] Tool call received: {fn_name} | Args: {args}")

        # Map tool name to action_type
        action_type = TOOL_ACTION_MAP.get(fn_name)
        if not action_type:
            results.append({
                "toolCallId": tool_call_id,
                "result": "I'm sorry, I don't recognize that action. Could you please rephrase your request?"
            })
            continue

        # Extract common fields
        amount = float(args.get("amount", 0))
        beneficiary_status = args.get("beneficiary_status", "EXISTING")

        # Determine customer_id:
        # - For verify_identity, use the customer_id from the tool args
        # - For all other tools, use the verified_customer_id from the current call session (if available)
        current_call_verified_id = verified_calls.get(call_id)
        if action_type == "VERIFY_IDENTITY":
            customer_id = args.get("customer_id", "")
        elif current_call_verified_id:
            customer_id = current_call_verified_id
        else:
            # Not yet verified — use a placeholder for risk evaluation
            # The risk engine will assess based on action signals + Moss context only
            customer_id = "UNVERIFIED_CALLER"

        # Build the action object
        action = AgentAction(
            action_id=f"VAPI_{tool_call_id[:8]}",
            customer_id=customer_id,
            action_type=action_type,
            amount=amount,
            beneficiary_status=beneficiary_status,
        )

        # Load customer profile from customers.json
        customer = load_customer(customer_id)
        if not customer:
            # No profile found — this is either an unverified caller or an unknown ID.
            # We use a high-baseline-risk "unknown" profile so the risk engine
            # naturally flags it for verification.
            customer = CustomerProfile(
                customer_id=customer_id,
                account_age=0,
                average_transaction_amount=0,
                transaction_frequency=0,
                known_devices=[],
                trusted_beneficiaries=[],
                baseline_risk=30,
            )

        # Build a rich, tool-specific query for Moss
        query = _build_moss_query(action_type, amount, args)
        
        start_backend = time.perf_counter()
        context_items, moss_ms = await search_context(query, top_k=5, customer_id=customer_id)
        risk_decision, eval_ms = evaluate_risk(action, customer, context_items)

        # Post-verification logic:
        # If the caller was already verified IN THIS SPECIFIC CALL, override the risk decision to ALLOW
        # because identity has been confirmed against behavioral history.
        verified_customer_id = verified_calls.get(call_id)
        
        if verified_customer_id and action_type != "VERIFY_IDENTITY":
            risk_decision.decision = "ALLOW"
            risk_decision.explanation = (
                f"Action authorized. Customer {verified_customer_id} identity was verified "
                f"against behavioral history. Original risk score was {risk_decision.risk_score}."
            )
            risk_decision.risk_score = 0
            # We DON'T delete it here so they stay verified for the rest of this phone call!

        # For VERIFY_IDENTITY: if the behavioral check doesn't hard-block,
        # treat it as a successful verification and store the customer_id for this call ID
        if action_type == "VERIFY_IDENTITY" and risk_decision.decision in ("VERIFY", "ALLOW", "ESCALATE"):
            risk_decision.decision = "ALLOW"
            risk_decision.explanation = "Identity successfully verified against behavioral history."
            verified_calls[call_id] = customer_id
            
        print(f"[VAPI] {fn_name} -> {risk_decision.decision} | Score: {risk_decision.risk_score} | Moss: {moss_ms:.1f}ms | Eval: {eval_ms:.1f}ms")

        # If action is ALLOWED and customer has an email on file,
        # DON'T send the email yet. Store a pending confirmation and
        # ask the user to type their registered email for verification.
        ask_for_email = False
        if risk_decision.decision == "ALLOW" and action_type != "VERIFY_IDENTITY":
            if getattr(customer, "email", None):
                pending_email_confirmation = {
                    "customer_email": customer.email,
                    "registered_email": customer.email,
                    "action_type": action_type,
                    "amount": amount,
                    "customer_id": customer_id,
                }
                ask_for_email = True
                print(f"[Email Service] Pending confirmation stored for {customer_id}. Waiting for email verification.")

        # Build a natural spoken response
        spoken = _build_spoken_response(
            action_type, risk_decision.decision, risk_decision.risk_score,
            risk_decision.explanation, amount
        )

        # Append email prompt if needed
        if ask_for_email:
            spoken += (
                " To receive a confirmation email, please type your registered email address "
                "into the email field in the chat box below."
            )

        results.append({
            "toolCallId": tool_call_id,
            "result": spoken,
        })
        
        # Store for the frontend UI
        recent_vapi_evaluations.append({
            "toolName": fn_name,
            "args": args,
            "decision": risk_decision.decision,
            "score": risk_decision.risk_score,
            "explanation": risk_decision.explanation,
            "moss_ms": round(moss_ms, 1),
            "eval_ms": round(eval_ms, 1),
            "timestamp": datetime.datetime.now().isoformat()
        })

    return {"results": results}
