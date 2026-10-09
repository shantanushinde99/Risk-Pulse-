"""
Offline check of the guardrail and VAPI webhook flow (Moss, Mistral and Mailjet stubbed).
Run from backend/:  python -m tests.test_guardrail
"""
from fastapi.testclient import TestClient

import app.main as main
import app.services.vapi_service as vapi
from app.models.schemas import AgentAction
from app.services.data_service import load_customer
from app.services.risk_engine import evaluate_risk

ATO_TIMELINE = [{"id": "TIMELINE_CUST_DEMO_ATO", "score": None, "text":
    "[METADATA: document_type: customer_timeline | customer_id: CUST_DEMO_ATO]\n"
    "NEW_DEVICE_LOGIN occurred. PASSWORD_RESET occurred. FAILED_OTP occurred."}]


async def fake_search(query, top_k=5, customer_id=None):
    return (ATO_TIMELINE if customer_id == "CUST_DEMO_ATO" else []), 1.0, 1.0

vapi.search_context = fake_search
main.search_context = fake_search
vapi.send_confirmation_email = lambda *a: True
main.generate_agent_response = lambda req, d: (d.decision, 0.0)
client = TestClient(main.app)


def tool(call_id, name, **args):
    body = {"message": {"type": "tool-calls", "call": {"id": call_id},
                        "toolCallList": [{"id": "t1", "type": "function", "function": {"name": name, "arguments": args}}]}}
    r = client.post("/api/vapi/webhook", json=body)
    assert r.status_code == 200, r.text
    return r.json()["results"][0]["result"]


def last_decision(call_id):
    return client.get(f"/api/agent/latest-evaluations?call_id={call_id}").json()["evaluations"][-1]["decision"]


def run():
    # Risk engine: signals count once, tiers ordered, failed retrieval fails safe
    safe = load_customer("CUST_DEMO_SAFE")
    act = AgentAction(action_id="a", customer_id=safe.customer_id, action_type="TRANSFER_MONEY", amount=100, beneficiary_status="EXISTING")
    assert evaluate_risk(act, safe, [])[0].decision == "ALLOW"
    assert evaluate_risk(act, safe, None)[0].decision == "VERIFY"
    dup = ATO_TIMELINE * 3
    signals = evaluate_risk(act, safe, dup)[0].signals
    assert len(signals) == len({s.name for s in signals})

    # Dashboard scenarios
    for sid, expected in [("safe", "ALLOW"), ("suspicious", "VERIFY"), ("ato", "BLOCK")]:
        assert client.post(f"/api/scenarios/{sid}/run").json()["decision"]["decision"] == expected, sid
    assert client.post("/api/evaluate-custom", json={"action_type": "HACK", "baseline_risk": 5}).status_code == 422

    # Unidentified caller cannot act
    assert "Customer ID" in tool("c1", "transfer_money", amount=500, beneficiary_name="John")
    assert last_decision("c1") == "VERIFY"

    # Account details are never shared before verification, and are real afterwards
    assert "Customer ID" in tool("c6", "get_account_summary")
    tool("c6", "verify_identity", customer_id="C9876543210")
    summary = tool("c6", "get_account_summary")
    assert "active" in summary and "sh***@gmail.com" in summary and "2433" not in summary

    # Fake IDs are rejected and lock the call after 3 tries
    for _ in range(3):
        tool("c2", "verify_identity", customer_id="FAKE123")
    assert last_decision("c2") == "BLOCK"
    tool("c2", "verify_identity", customer_id="C9876543210")
    assert vapi.sessions["c2"]["customer_id"] is None

    # ATO account is blocked at verification
    tool("c3", "verify_identity", customer_id="cust_demo_ato")
    assert last_decision("c3") == "BLOCK" and vapi.sessions["c3"]["locked"]

    # Real customer: transfer to unknown payee needs email step-up, then succeeds once
    tool("c4", "verify_identity", customer_id="C 9876 543210")
    assert vapi.sessions["c4"]["customer_id"] == "C9876543210"
    assert "email" in tool("c4", "transfer_money", amount="3000", beneficiary_name="John", beneficiary_status="EXISTING")
    assert last_decision("c4") == "VERIFY"
    bad = client.post("/api/agent/verify-email", json={"call_id": "c4", "email": "attacker@evil.com"}).json()
    assert bad["verified"] is False
    good = client.post("/api/agent/verify-email", json={"call_id": "c4", "email": "ShantanuShinde2433@gmail.com"}).json()
    assert good["verified"] is True
    assert "processed successfully" in tool("c4", "transfer_money", amount=3000, beneficiary_name="John")
    assert last_decision("c4") == "ALLOW"
    tool("c4", "transfer_money", amount=3000, beneficiary_name="John")
    assert last_decision("c4") == "VERIFY"  # step-up is one-shot

    # Large transfer escalates to a human
    tool("c4", "transfer_money", amount=50000, beneficiary_name="John")
    assert last_decision("c4") == "ESCALATE"

    # Session ends with the call; string-encoded arguments are accepted
    client.post("/api/vapi/webhook", json={"message": {"type": "end-of-call-report", "call": {"id": "c4"}}})
    assert "c4" not in vapi.sessions
    body = {"message": {"type": "tool-calls", "call": {"id": "c5"}, "toolCallList": [
        {"id": "x", "function": {"name": "verify_identity", "arguments": '{"customer_id": "CUST_DEMO_SAFE"}'}}]}}
    assert "located your account" in client.post("/api/vapi/webhook", json=body).json()["results"][0]["result"]

    print("All guardrail checks passed.")


if __name__ == "__main__":
    run()
