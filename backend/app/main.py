import os
import hmac
import json
import time
import asyncio
from contextlib import asynccontextmanager
from typing import Literal, Optional
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

from app.models.schemas import ScenarioResponse, AgentAction, CustomerProfile
from app.services.data_service import get_scenario_data, load_customer
from app.services.moss_service import search_context, warm_up
from app.services.risk_engine import evaluate_risk
from app.services.agent_service import generate_agent_response
from app.services import vapi_service

VAPI_WEBHOOK_SECRET = os.getenv("VAPI_WEBHOOK_SECRET")


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(warm_up())  # don't block startup on the Moss download
    yield


app = FastAPI(title="RiskPulse API", version="1.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


# ─────────────────────────────────────────────
# Dashboard: scenarios and sandbox
# ─────────────────────────────────────────────

def _build_query(action: AgentAction, customer: CustomerProfile) -> str:
    query = f"Evaluate risk for {action.action_type} of {action.amount}. Customer baseline risk {customer.baseline_risk}."
    if action.beneficiary_status == "NEW":
        query += " New beneficiary added."
    if action.action_type in ["CHANGE_PHONE", "CHANGE_EMAIL"]:
        query += " Account details changed."
    return query


async def _evaluate(action: AgentAction, customer: CustomerProfile, customer_request: str) -> ScenarioResponse:
    start = time.perf_counter()
    context, embed_ms, moss_ms = await search_context(_build_query(action, customer), top_k=5, customer_id=customer.customer_id)
    decision, eval_ms = evaluate_risk(action, customer, context)
    guardrail_ms = (time.perf_counter() - start) * 1000

    final_response, llm_ms = await asyncio.to_thread(generate_agent_response, customer_request, decision)

    return ScenarioResponse(
        customer_request=customer_request,
        action=action,
        embedding_latency_ms=round(embed_ms, 2),
        moss_latency_ms=round(moss_ms, 2),
        backend_latency_ms=round(guardrail_ms - embed_ms - moss_ms, 2),
        risk_evaluation_latency_ms=round(eval_ms, 2),
        total_guardrail_latency_ms=round(guardrail_ms, 2),
        llm_latency_ms=round(llm_ms, 2),
        decision=decision,
        final_response=final_response,
    )


@app.get("/api/scenarios")
def list_scenarios():
    return {
        "scenarios": [
            {"id": "safe", "name": "Safe Transaction"},
            {"id": "suspicious", "name": "Suspicious Request"},
            {"id": "ato", "name": "Account Takeover"},
        ]
    }


@app.post("/api/scenarios/{scenario_id}/run", response_model=ScenarioResponse)
async def run_scenario(scenario_id: str):
    scenario = get_scenario_data(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    action = AgentAction(**scenario["action"])
    customer = load_customer(action.customer_id)
    if not customer:
        raise HTTPException(status_code=500, detail=f"Demo customer {action.customer_id} missing from customers.json")

    return await _evaluate(action, customer, scenario["request"])


class CustomEvaluationRequest(BaseModel):
    action_type: Literal["TRANSFER_MONEY", "CHANGE_PHONE", "CHANGE_EMAIL", "ADD_BENEFICIARY", "RESET_PIN", "CLOSE_ACCOUNT"]
    amount: float = Field(default=0, ge=0, le=10_000_000)
    beneficiary_status: Optional[Literal["NEW", "EXISTING"]] = None
    baseline_risk: int = Field(ge=0, le=100)


@app.post("/api/evaluate-custom", response_model=ScenarioResponse)
async def evaluate_custom(req: CustomEvaluationRequest):
    action = AgentAction(
        action_id="CUSTOM_123",
        customer_id="CUST_CUSTOM",
        action_type=req.action_type,
        amount=req.amount if req.action_type == "TRANSFER_MONEY" else None,
        beneficiary_status=req.beneficiary_status if req.action_type in ("TRANSFER_MONEY", "ADD_BENEFICIARY") else None,
    )
    customer = CustomerProfile(
        customer_id="CUST_CUSTOM",
        account_age=365,
        average_transaction_amount=1000,
        transaction_frequency=10,
        known_devices=[],
        trusted_beneficiaries=[],
        baseline_risk=req.baseline_risk,
    )
    return await _evaluate(action, customer, "Custom request via Sandbox")


# ─────────────────────────────────────────────
# VAPI voice agent
# ─────────────────────────────────────────────

@app.post("/api/vapi/webhook")
async def vapi_webhook(request: Request, x_vapi_secret: Optional[str] = Header(default=None)):
    if VAPI_WEBHOOK_SECRET and not hmac.compare_digest(x_vapi_secret or "", VAPI_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    message = (await request.json()).get("message") or {}
    call_id = (message.get("call") or {}).get("id") or "unknown-call"
    msg_type = message.get("type")

    if msg_type == "tool-calls":
        results = []
        for tool_call in message.get("toolCallList") or []:
            fn = tool_call.get("function") or {}
            args = fn.get("arguments") or {}
            try:
                if isinstance(args, str):
                    args = json.loads(args or "{}")
                result = await vapi_service.handle_tool_call(call_id, fn.get("name"), args)
            except Exception as e:  # fail closed: never let an error turn into an executed action
                print(f"[VAPI] Tool {fn.get('name')} failed: {e}")
                result = "I'm sorry, I can't complete that request right now. Please try again in a moment."
            results.append({"toolCallId": tool_call.get("id"), "result": result})
        return {"results": results}

    if msg_type == "end-of-call-report":
        vapi_service.end_session(call_id)

    return {}


@app.get("/api/agent/latest-evaluations")
def get_latest_agent_evaluations(call_id: Optional[str] = None):
    evals = [e for e in vapi_service.evaluations if call_id is None or e["call_id"] == call_id]
    return {"evaluations": evals[-20:]}


class VerifyIdRequest(BaseModel):
    call_id: str = Field(min_length=1, max_length=128)
    customer_id: str = Field(min_length=1, max_length=64)


@app.post("/api/agent/verify-id")
async def verify_id(req: VerifyIdRequest):
    return await vapi_service.verify_customer_id(req.call_id, req.customer_id)


class VerifyEmailRequest(BaseModel):
    call_id: str = Field(min_length=1, max_length=128)
    email: str = Field(min_length=3, max_length=254)


@app.post("/api/agent/verify-email")
def verify_email(req: VerifyEmailRequest):
    return vapi_service.verify_email(req.call_id, req.email)
