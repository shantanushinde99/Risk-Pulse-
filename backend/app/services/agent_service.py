import os
import time
import requests
from typing import Tuple
from dotenv import load_dotenv
from app.models.schemas import RiskDecision

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))

MISTRAL_API_KEY = os.getenv("LLM_API_KEY")
MISTRAL_MODEL = os.getenv("LLM_MODEL", "mistral-large-latest")

def get_fallback_response(decision: str) -> str:
    if decision == "ALLOW":
        return "I've gone ahead and processed that request for you successfully. Is there anything else you need?"
    elif decision == "VERIFY":
        return "I'd love to help with that, but for your security, I just need to quickly verify your identity first. A link has been sent to your registered device."
    elif decision == "BLOCK":
        return "I'm sorry, but for your security, I can't process this action right now because we couldn't fully authenticate the request. Please visit a branch or contact our fraud department."
    elif decision == "ESCALATE":
        return "I think it's best if a specialist handles this for you. Let me quickly connect you to a human agent who can help."
    return "I'm processing that right now."

def generate_agent_response(customer_request: str, risk_decision: RiskDecision) -> Tuple[str, float]:
    start_time = time.perf_counter()
    
    decision_status = risk_decision.decision
    explanation = risk_decision.explanation
    
    if MISTRAL_API_KEY:
        prompt = f"""
You are a helpful, professional, and secure AI banking voice agent speaking directly to a customer.
A customer has requested the following: "{customer_request}"

Your internal security guardrail returned this decision: {decision_status}
Internal Reason: {explanation}

Based on this decision, generate exactly what you will say out loud to the customer. 
CRITICAL RULES:
1. DO NOT mention "risk scores", "RiskPulse", "confidence levels", or "internal security systems".
2. Sound conversational, natural, and empathetic (1-2 short sentences maximum).
3. If ALLOW: Politely confirm the action was processed successfully.
4. If VERIFY: Tell them you need to send a quick verification code or link for their security.
5. If BLOCK: Tell them you cannot process this right now because their identity could not be fully authenticated, or frame it creatively as a routine security measure. Never say "you are blocked".
6. If ESCALATE: Tell them you are connecting them to a human specialist.

What do you say to the customer?
"""
        try:
            headers = {
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": MISTRAL_MODEL,
                "messages": [{"role": "user", "content": prompt}]
            }
            res = requests.post("https://api.mistral.ai/v1/chat/completions", json=payload, headers=headers, timeout=5.0)
            if res.status_code == 200:
                response_text = res.json()["choices"][0]["message"]["content"].strip()
                end_time = time.perf_counter()
                return response_text, (end_time - start_time) * 1000
            else:
                print(f"Mistral API Error: {res.text}")
        except Exception as e:
            print(f"LLM generation failed: {e}. Using fallback.")
            pass

    # Fallback if no client or error
    response_text = get_fallback_response(decision_status)
    end_time = time.perf_counter()
    return response_text, (end_time - start_time) * 1000
