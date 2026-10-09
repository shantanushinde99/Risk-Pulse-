import re
import time
from typing import List, Optional, Tuple
from app.models.schemas import AgentAction, CustomerProfile, RiskDecision, RiskSignal, RiskContextItem

# Decision tiers, in increasing severity
BLOCK_AT = 85
ESCALATE_AT = 60
VERIFY_AT = 30

DOC_TYPE_RE = re.compile(r"document_type: (\w+)")
DOC_TYPE_LABELS = {
    "policy": "Policy",
    "historical_case": "Historical Case",
    "customer_timeline": "Customer Timeline",
    "paysim_transaction": "Transaction Record",
}

# Fixed per-action penalties: action_type -> (signal name, impact)
ACTION_RULES = {
    "CHANGE_PHONE": ("Account detail change requested", 25),
    "CHANGE_EMAIL": ("Account detail change requested", 25),
    "ADD_BENEFICIARY": ("Adding new payee (precursor to transfer)", 15),
    "RESET_PIN": ("PIN reset requested via voice", 20),
    "INCREASE_CREDIT_LIMIT": ("Credit limit increase request", 15),
    "ENABLE_INTL_TXN": ("International transactions enablement", 20),
    "CLOSE_ACCOUNT": ("Account closure request via voice", 25),
    "WITHDRAW_FD": ("Fixed deposit premature withdrawal", 20),
}

# Timeline event markers: keyword -> (signal name, impact)
TIMELINE_RULES = {
    "new_device_login": ("New device login on record", 20),
    "password_reset": ("Password reset on record", 25),
    "failed_otp": ("Failed OTP attempts on record", 20),
    "suspicious_location_change": ("Suspicious location change on record", 15),
}


def doc_type(text: str) -> str:
    m = DOC_TYPE_RE.search(text)
    return DOC_TYPE_LABELS.get(m.group(1), "Unknown") if m else "Unknown"


def decide(score: int) -> Tuple[str, str]:
    if score >= BLOCK_AT:
        return "BLOCK", "High-confidence risk pattern detected. Action blocked to prevent potential fraud or account takeover."
    if score >= ESCALATE_AT:
        return "ESCALATE", "Elevated risk. Escalating to a human agent for review."
    if score >= VERIFY_AT:
        return "VERIFY", "Suspicious signals detected. Additional verification is required before proceeding."
    return "ALLOW", "No significant risk signals detected. Action allowed."


def evaluate_risk(
    action: AgentAction,
    customer: CustomerProfile,
    context_items: Optional[List[dict]],
) -> Tuple[RiskDecision, float]:
    """
    Deterministic risk evaluation. `context_items` is the Moss retrieval result,
    or None when retrieval failed (which fails safe with a penalty).
    Returns (RiskDecision, evaluation_latency_ms).
    """
    start_time = time.perf_counter()

    score = customer.baseline_risk
    signals: List[RiskSignal] = []
    seen = set()

    def add(name: str, impact: int):
        nonlocal score
        if name in seen:  # each signal counts once, however many docs repeat it
            return
        seen.add(name)
        signals.append(RiskSignal(name=name, impact=impact))
        score += impact

    # 1. Action-based rules
    if action.amount and customer.average_transaction_amount:
        if action.amount > customer.average_transaction_amount * 3:
            add("Unusually high amount (>3x avg)", 30)
        elif action.amount > customer.average_transaction_amount * 1.5:
            add("High amount (>1.5x avg)", 15)

    if action.beneficiary_status == "NEW":
        add("New beneficiary", 20)

    if action.action_type in ACTION_RULES:
        add(*ACTION_RULES[action.action_type])

    if action.action_type == "INCREASE_CREDIT_LIMIT" and action.amount and action.amount > 200000:
        add("Very high credit limit requested (>2L)", 20)
    if action.action_type == "CLOSE_ACCOUNT" and customer.account_age < 180:
        add("Account less than 6 months old", 15)
    if action.action_type == "WITHDRAW_FD" and action.amount and action.amount > 500000:
        add("Large FD withdrawal (>5L)", 20)

    # 2. Contextual rules from Moss
    if context_items is None:
        add("Risk context unavailable (fail-safe)", 30)

    context_objs = []
    for ctx in context_items or []:
        raw = ctx.get("text", "")
        text = raw.lower()
        ctype = doc_type(raw)

        if ctype == "Customer Timeline":
            for keyword, rule in TIMELINE_RULES.items():
                if keyword in text:
                    add(*rule)

        # Precedent and policy signals only reinforce an already-suspicious picture
        if ctype == "Historical Case" and ("account takeover" in text or "fraud" in text) and score > 50:
            add("Matches historical account takeover pattern", 20)

        if ctype == "Policy" and "blocked" in text and score > 60:
            add("Violates high-risk policy", 15)

        context_objs.append(RiskContextItem(
            source="Moss Retrieval",
            type=ctype,
            relevance="Relevant",
            content=raw[:300] + "..." if len(raw) > 300 else raw,
            metadata={"score": ctx.get("score")},
        ))

    score = max(0, min(score, 100))
    decision, explanation = decide(score)
    confidence = min(0.99, 0.5 + (score / 200.0) if score > 50 else 0.5 + ((100 - score) / 200.0))

    rd = RiskDecision(
        risk_score=score,
        decision=decision,
        confidence=confidence,
        signals=signals,
        retrieved_context=context_objs,
        explanation=explanation,
    )
    return rd, (time.perf_counter() - start_time) * 1000
