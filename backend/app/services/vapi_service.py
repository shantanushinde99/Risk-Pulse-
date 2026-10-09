"""
VAPI tool-call handling: per-call sessions, identity verification, email step-up,
and routing every banking tool through the RiskPulse guardrail.
"""
import re
import random
import string
import asyncio
import datetime
from collections import deque
from typing import Optional

from app.models.schemas import AgentAction, CustomerProfile
from app.services.data_service import load_customer
from app.services.moss_service import search_context
from app.services.risk_engine import evaluate_risk
from app.services.email_service import send_confirmation_email

MAX_ATTEMPTS = 3

# tool name -> (action_type, spoken label, name of the amount argument or None)
TOOL_ACTIONS = {
    "transfer_money": ("TRANSFER_MONEY", "transfer", "amount"),
    "change_phone_number": ("CHANGE_PHONE", "phone number change", None),
    "change_email": ("CHANGE_EMAIL", "email address change", None),
    "process_refund": ("PROCESS_REFUND", "refund", "amount"),
    "add_beneficiary": ("ADD_BENEFICIARY", "new beneficiary addition", None),
    "reset_pin": ("RESET_PIN", "PIN reset", None),
    "increase_credit_limit": ("INCREASE_CREDIT_LIMIT", "credit limit increase", "amount"),
    "enable_international_transactions": ("ENABLE_INTL_TXN", "international transaction enablement", None),
    "close_account": ("CLOSE_ACCOUNT", "account closure", None),
    "withdraw_fixed_deposit": ("WITHDRAW_FD", "fixed deposit withdrawal", "amount"),
}

MOSS_QUERIES = {
    "TRANSFER_MONEY": "Risk assessment for money transfer of {amount}. Check for fraud patterns, suspicious beneficiary, and velocity limits.",
    "CHANGE_PHONE": "Customer requesting phone number change. Check for account takeover patterns, recent suspicious activity, and identity verification policies.",
    "CHANGE_EMAIL": "Customer requesting email address change. Check for account takeover patterns and credential change policies.",
    "PROCESS_REFUND": "Customer requesting refund of {amount}. Check for refund abuse patterns and refund fraud policies.",
    "ADD_BENEFICIARY": "Customer adding a new beneficiary. Check for social engineering patterns, mule account indicators, and beneficiary policies.",
    "RESET_PIN": "Customer requesting PIN reset via voice channel. Check for unauthorized access attempts and PIN reset policies.",
    "INCREASE_CREDIT_LIMIT": "Customer requesting credit limit increase to {amount}. Check for credit fraud patterns and eligibility policies.",
    "ENABLE_INTL_TXN": "Customer requesting to enable international transactions. Check for card cloning, cross-border fraud patterns, and international transaction policies.",
    "CLOSE_ACCOUNT": "Customer requesting account closure via voice. Check for coerced closure patterns, elder abuse indicators, and account closure policies.",
    "WITHDRAW_FD": "Customer requesting premature fixed deposit withdrawal of {amount}. Check for coerced withdrawal patterns and FD withdrawal policies.",
    "VERIFY_IDENTITY": "Analyze behavioral risk and account takeover indicators for customer {customer_id}. Check for suspicious activity or high risk baseline.",
}

# ponytail: in-memory state, single process only; move to Redis if running >1 worker
sessions: dict[str, dict] = {}
evaluations: deque = deque(maxlen=200)
_background: set = set()  # keeps fire-and-forget email tasks alive until done


def _new_session() -> dict:
    return {
        "customer_id": None,
        "id_attempts": 0,
        "email_attempts": 0,
        "email_verified": False,  # one-shot step-up, consumed by the next VERIFY decision
        "locked": False,
    }


def get_session(call_id: str) -> dict:
    return sessions.setdefault(call_id, _new_session())


def end_session(call_id: str):
    sessions.pop(call_id, None)


def _ref() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def normalize_customer_id(raw) -> str:
    # Speech-to-text often inserts spaces or punctuation ("C 1231-006815")
    return re.sub(r"[^A-Za-z0-9_]", "", str(raw or "")).upper()


def _to_amount(raw) -> float:
    try:
        return max(float(str(raw).replace(",", "")), 0.0)
    except (TypeError, ValueError):
        return 0.0


def _record(call_id: str, tool: str, args: dict, decision: str, explanation: str,
            score: Optional[int] = None, embed_ms: float = 0.0, moss_ms: float = 0.0, eval_ms: float = 0.0):
    evaluations.append({
        "call_id": call_id,
        "toolName": tool,
        "args": args,
        "decision": decision,
        "score": score,
        "explanation": explanation,
        "embed_ms": round(embed_ms, 1),
        "moss_ms": round(moss_ms, 1),
        "eval_ms": round(eval_ms, 1),
        "timestamp": datetime.datetime.now().isoformat(),
    })


async def _guardrail(action: AgentAction, customer: CustomerProfile, query: str):
    context, embed_ms, moss_ms = await search_context(query, top_k=5, customer_id=customer.customer_id)
    decision, eval_ms = evaluate_risk(action, customer, context)
    return decision, embed_ms, moss_ms, eval_ms


async def _verify_identity(call_id: str, session: dict, args: dict) -> str:
    customer_id = normalize_customer_id(args.get("customer_id"))
    customer = load_customer(customer_id) if customer_id else None

    if not customer:
        session["id_attempts"] += 1
        explanation = f"No account found for Customer ID '{customer_id}' (attempt {session['id_attempts']}/{MAX_ATTEMPTS})."
        if session["id_attempts"] >= MAX_ATTEMPTS:
            session["locked"] = True
            explanation += " Session locked."
        _record(call_id, "verify_identity", args, "BLOCK", explanation, 100)
        if session["locked"]:
            return ("I'm sorry, I wasn't able to verify your identity. For your security I can't continue on this call. "
                    f"Please visit your nearest branch with a valid photo ID. Your reference number is {_ref()}.")
        return "I couldn't find an account with that Customer ID. Please check it and enter it again in the Customer ID box on your screen."

    action = AgentAction(action_id=f"VAPI_{_ref()}", customer_id=customer_id, action_type="VERIFY_IDENTITY")
    decision, embed_ms, moss_ms, eval_ms = await _guardrail(
        action, customer, MOSS_QUERIES["VERIFY_IDENTITY"].format(customer_id=customer_id))

    if decision.decision == "BLOCK":
        session["locked"] = True
        _record(call_id, "verify_identity", args, "BLOCK",
                f"Account shows a high-risk takeover pattern. {decision.explanation}",
                decision.risk_score, embed_ms, moss_ms, eval_ms)
        return ("I've located your account, but I'm unable to authenticate you over the phone right now. "
                f"Please visit your nearest branch with a valid photo ID. Your reference number is {_ref()}.")

    session.update(customer_id=customer_id, email_verified=False, email_attempts=0)
    _record(call_id, "verify_identity", args, "ALLOW",
            f"Customer {customer_id} identified. Account risk score {decision.risk_score}; actions are still evaluated individually.",
            decision.risk_score, embed_ms, moss_ms, eval_ms)
    name = f", {customer.name.split()[0]}" if customer.name else ""
    return f"Thank you{name}, I've located your account. Please go ahead with your request."


def _mask_email(email: str) -> str:
    user, _, domain = email.partition("@")
    return f"{user[:2]}***@{domain}"


def _account_summary(call_id: str, session: dict) -> str:
    """Read-only account facts for a verified caller; never exposes risk data."""
    if not session["customer_id"]:
        _record(call_id, "get_account_summary", {}, "VERIFY", "Caller not identified. Customer ID required before sharing account details.")
        return "I can check that for you. First, I need to verify your identity. Please type your Customer ID into the Customer ID box on your screen, or read it out to me."

    customer = load_customer(session["customer_id"])
    _record(call_id, "get_account_summary", {}, "ALLOW", f"Read-only account summary shared with verified customer {customer.customer_id}.")
    years, days = divmod(customer.account_age, 365)
    age = f"{years} year{'s' if years != 1 else ''}" if years else f"{max(days // 30, 1)} month(s)"
    payees = len(customer.trusted_beneficiaries)
    email = f" Your registered email is {_mask_email(customer.email)}." if customer.email else " There's no email address registered on your account."
    return (f"Your account is active and has been open for about {age}. "
            f"You have {payees} saved payee{'s' if payees != 1 else ''}.{email}")


async def handle_tool_call(call_id: str, tool: str, args: dict) -> str:
    """Run one VAPI tool call through RiskPulse and return what the assistant should say."""
    args = args or {}
    session = get_session(call_id)

    if session["locked"]:
        _record(call_id, tool, args, "BLOCK", "Session locked after failed or high-risk verification.", 100)
        return "I'm sorry, I can't help with any account requests on this call. Please visit your nearest branch with a valid photo ID."

    if tool == "verify_identity":
        return await _verify_identity(call_id, session, args)

    if tool == "get_account_summary":
        return _account_summary(call_id, session)

    if tool not in TOOL_ACTIONS:
        return "Sorry, I can't help with that request."

    action_type, label, amount_arg = TOOL_ACTIONS[tool]

    # Secure by default: nothing runs for an unidentified caller
    if not session["customer_id"]:
        _record(call_id, tool, args, "VERIFY", "Caller not identified. Customer ID required before any action.")
        return f"I can help with the {label}. First, I need to verify your identity. Please type your Customer ID into the Customer ID box on your screen, or read it out to me."

    customer = load_customer(session["customer_id"])
    amount = _to_amount(args.get(amount_arg)) if amount_arg else None

    # Beneficiary is trusted only if the account is on file, never on the caller's word
    beneficiary_status = None
    if action_type == "TRANSFER_MONEY":
        account = str(args.get("beneficiary_account") or "").strip()
        beneficiary_status = "EXISTING" if account and account in customer.trusted_beneficiaries else "NEW"

    action = AgentAction(
        action_id=f"VAPI_{_ref()}",
        customer_id=customer.customer_id,
        action_type=action_type,
        amount=amount,
        beneficiary_status=beneficiary_status,
    )
    decision, embed_ms, moss_ms, eval_ms = await _guardrail(
        action, customer, MOSS_QUERIES[action_type].format(amount=amount or 0))

    outcome, explanation = decision.decision, decision.explanation
    if outcome == "VERIFY" and session["email_verified"]:
        session["email_verified"] = False
        outcome = "ALLOW"
        explanation = f"Step-up passed: registered email confirmed. Original decision VERIFY (score {decision.risk_score})."

    _record(call_id, tool, args, outcome, explanation, decision.risk_score, embed_ms, moss_ms, eval_ms)

    ref = _ref()
    if outcome == "BLOCK":
        return (f"I'm sorry, but I can't process this {label} right now for your security. "
                f"Please visit your nearest branch with a valid photo ID, or contact our support team. Your reference number is {ref}.")
    if outcome == "ESCALATE":
        return (f"I think it's best if a specialist handles this {label} for you. "
                f"Let me connect you to a human agent. Please hold. Your reference number is {ref}.")
    if outcome == "VERIFY":
        if not customer.email:
            return (f"This {label} needs additional verification, and there's no email on file for your account. "
                    f"Please visit your nearest branch to complete it. Your reference number is {ref}.")
        return (f"For your security, this {label} needs one more check. Please type your registered email address "
                f"into the Registered email box on your screen.")

    if customer.email:
        task = asyncio.create_task(asyncio.to_thread(send_confirmation_email, customer.email, action_type, amount))
        _background.add(task)
        task.add_done_callback(_background.discard)
    amt_text = f" of {int(amount):,} rupees" if amount else ""
    return (f"Done. Your {label}{amt_text} has been processed successfully, and a confirmation has been sent to your email. "
            f"Your confirmation number is {ref}. Is there anything else I can help you with?")


async def verify_customer_id(call_id: str, customer_id: str) -> dict:
    """Typed Customer ID from the web UI; same checks, attempt limits and lock-out as the voice tool."""
    message = await handle_tool_call(call_id, "verify_identity", {"customer_id": customer_id})
    session = get_session(call_id)
    return {"verified": bool(session["customer_id"]), "locked": session["locked"], "message": message}


def verify_email(call_id: str, email: str) -> dict:
    """Step-up check: the caller types the account's registered email on screen."""
    session = sessions.get(call_id)
    if not session or not session["customer_id"]:
        return {"verified": False, "message": "Verify your Customer ID with the agent first."}
    if session["locked"] or session["email_attempts"] >= MAX_ATTEMPTS:
        session["locked"] = True
        return {"verified": False, "message": "Too many attempts. This call is locked."}

    customer = load_customer(session["customer_id"])
    registered = (customer.email or "").strip().lower()
    if registered and email.strip().lower() == registered:
        session["email_verified"] = True
        session["email_attempts"] = 0
        return {"verified": True, "message": "Email verified."}

    session["email_attempts"] += 1
    left = MAX_ATTEMPTS - session["email_attempts"]
    if left <= 0:
        session["locked"] = True
    return {"verified": False, "message": f"Email does not match the registered account. {left} attempt(s) left."}
