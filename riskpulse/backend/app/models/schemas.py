from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class CustomerProfile(BaseModel):
    customer_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    account_age: int # in days
    average_transaction_amount: float
    transaction_frequency: float # per month
    known_devices: List[str]
    trusted_beneficiaries: List[str]
    baseline_risk: int = Field(ge=0, le=100)

class SecurityEvent(BaseModel):
    event_id: str
    customer_id: str
    timestamp: datetime
    event_type: str
    severity: str # LOW, MEDIUM, HIGH, CRITICAL
    details: str
    metadata: Dict[str, Any] = {}

class AgentAction(BaseModel):
    action_id: str
    customer_id: str
    action_type: str # TRANSFER_MONEY, CHANGE_PHONE, etc.
    amount: Optional[float] = None
    beneficiary_status: Optional[str] = None # NEW, EXISTING
    status: str = "PENDING_RISK_CHECK"

class RiskSignal(BaseModel):
    name: str
    impact: int

class RiskContextItem(BaseModel):
    source: str # e.g. "Security Policy", "Historical Fraud Case", "Recent Event"
    type: str
    relevance: str
    content: str
    metadata: Dict[str, Any] = {}

class RiskDecision(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    decision: str # ALLOW, VERIFY, BLOCK, ESCALATE
    confidence: float
    signals: List[RiskSignal]
    retrieved_context: List[RiskContextItem]
    explanation: str

class CustomerRequest(BaseModel):
    text: str

class ScenarioResponse(BaseModel):
    customer_request: str
    action: AgentAction
    moss_latency_ms: float
    backend_latency_ms: float
    risk_evaluation_latency_ms: float
    total_guardrail_latency_ms: float
    llm_latency_ms: Optional[float] = None
    decision: RiskDecision
    final_response: str
