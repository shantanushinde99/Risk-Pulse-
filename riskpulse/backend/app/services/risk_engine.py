import time
from typing import List, Tuple
from app.models.schemas import AgentAction, CustomerProfile, RiskDecision, RiskSignal, RiskContextItem

def evaluate_risk(
    action: AgentAction, 
    customer: CustomerProfile, 
    context_items: List[dict]
) -> Tuple[RiskDecision, float]:
    """
    Evaluates the risk of an action deterministically based on context.
    Returns a tuple of (RiskDecision, evaluation_latency_ms)
    """
    start_time = time.perf_counter()
    
    score = customer.baseline_risk
    signals = []
    
    # 1. Action-based rules
    if action.amount and customer.average_transaction_amount:
        if action.amount > customer.average_transaction_amount * 3:
            signals.append(RiskSignal(name="Unusually high amount (3x avg)", impact=30))
            score += 30
        elif action.amount > customer.average_transaction_amount * 1.5:
            signals.append(RiskSignal(name="High amount (1.5x avg)", impact=15))
            score += 15
            
    if action.beneficiary_status == "NEW":
        signals.append(RiskSignal(name="New beneficiary", impact=20))
        score += 20
        
    if action.action_type in ["CHANGE_PHONE", "CHANGE_EMAIL"]:
        signals.append(RiskSignal(name="Account detail change requested", impact=25))
        score += 25

    # Action-type-specific rules for expanded tools
    if action.action_type == "ADD_BENEFICIARY":
        signals.append(RiskSignal(name="Adding new payee (precursor to transfer)", impact=15))
        score += 15

    if action.action_type == "RESET_PIN":
        signals.append(RiskSignal(name="PIN reset requested via voice", impact=20))
        score += 20

    if action.action_type == "INCREASE_CREDIT_LIMIT":
        signals.append(RiskSignal(name="Credit limit increase request", impact=15))
        score += 15
        if action.amount and action.amount > 200000:
            signals.append(RiskSignal(name="Very high credit limit requested (>2L)", impact=20))
            score += 20

    if action.action_type == "ENABLE_INTL_TXN":
        signals.append(RiskSignal(name="International transactions enablement", impact=20))
        score += 20

    if action.action_type == "CLOSE_ACCOUNT":
        signals.append(RiskSignal(name="Account closure request via voice", impact=25))
        score += 25
        if customer.account_age and customer.account_age < 180:
            signals.append(RiskSignal(name="Account less than 6 months old", impact=15))
            score += 15

    if action.action_type == "WITHDRAW_FD":
        signals.append(RiskSignal(name="Fixed deposit premature withdrawal", impact=20))
        score += 20
        if action.amount and action.amount > 500000:
            signals.append(RiskSignal(name="Large FD withdrawal (>5L)", impact=20))
            score += 20

    # 2. Contextual rules from Moss
    # We look for keywords in the retrieved context items that indicate risk
    context_objs = []
    for ctx in context_items:
        text = ctx.get("text", "").lower()
        
        # Determine source/type purely by parsing what we ingested
        ctype = "Unknown"
        if "policy:" in text:
            ctype = "Policy"
        elif "case:" in text:
            ctype = "Historical Case"
        elif "timeline" in text:
            ctype = "Customer Timeline"
            
        relevance = "Relevant"
        
        # Analyze timeline events
        if ctype == "Customer Timeline":
            if "new_device_login" in text:
                signals.append(RiskSignal(name="Recent new device login", impact=20))
                score += 20
            if "password_reset" in text:
                signals.append(RiskSignal(name="Recent password reset", impact=25))
                score += 25
            if "failed_otp" in text:
                signals.append(RiskSignal(name="Recent failed OTP attempts", impact=20))
                score += 20
                
        # Analyze historical cases
        if ctype == "Historical Case":
            if "account takeover" in text or "fraud" in text:
                if score > 50: # Only applies if we already have suspicious signals
                    signals.append(RiskSignal(name="Matches historical account takeover pattern", impact=20))
                    score += 20
                    
        # Analyze policies
        if ctype == "Policy":
            if "blocked" in text and score > 60:
                signals.append(RiskSignal(name="Violates high-risk policy", impact=15))
                score += 15

        context_objs.append(RiskContextItem(
            source="Moss Retrieval",
            type=ctype,
            relevance=relevance,
            content=ctx.get("text", "")[:300] + "..." if len(ctx.get("text", "")) > 300 else ctx.get("text", ""),
            metadata={"score": ctx.get("score")}
        ))
        
    # Cap score at 100
    score = min(score, 100)
    score = max(score, 0)
    
    # Decision Logic
    if score >= 85:
        decision = "BLOCK"
        explanation = "High-confidence risk pattern detected. Action blocked to prevent potential fraud or account takeover."
    elif score >= 40:
        decision = "VERIFY"
        explanation = "Suspicious signals detected. Additional verification is required before proceeding."
    elif score >= 20:
        decision = "ESCALATE"
        explanation = "Moderate risk. Escalating to a human agent for review."
    else:
        decision = "ALLOW"
        explanation = "No significant risk signals detected. Action allowed."

    confidence = min(0.99, 0.5 + (score / 200.0) if score > 50 else 0.5 + ((100 - score) / 200.0))
    
    end_time = time.perf_counter()
    evaluation_latency_ms = (end_time - start_time) * 1000
    
    rd = RiskDecision(
        risk_score=score,
        decision=decision,
        confidence=confidence,
        signals=signals,
        retrieved_context=context_objs,
        explanation=explanation
    )
    
    return rd, evaluation_latency_ms
