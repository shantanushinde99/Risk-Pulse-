"""
RiskPulse LiveKit Voice Agent
=============================
A LiveKit Agent worker that intercepts all high-risk banking tool calls
through the RiskPulse guardrail (Moss semantic search + deterministic risk engine).

Uses:
  - AssemblyAI for Speech-to-Text
  - OpenAI for LLM (function calling) and Text-to-Speech
"""

import os
import sys
import time
import random
import string
import asyncio
import datetime
import logging

from dotenv import load_dotenv

# ── LiveKit Agents ──────────────────────────────────────────────────
from livekit import agents
from livekit.agents import (
    AgentSession,
    Agent,
    RunContext,
    function_tool,
    WorkerOptions,
    AutoSubscribe,
)
from livekit.plugins import assemblyai, openai

# ── RiskPulse Services (reuse existing backend logic) ──────────────
# Adjust path so we can import from the app package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.schemas import AgentAction, CustomerProfile
from app.services.data_service import load_customer
from app.services.moss_service import search_context
from app.services.risk_engine import evaluate_risk
from app.services.email_service import send_confirmation_email

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

logger = logging.getLogger("riskpulse-agent")


# ─────────────────────────────────────────────────────────────────────
# Shared State (for the dashboard via HTTP callback)
# ─────────────────────────────────────────────────────────────────────
FASTAPI_URL = os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:8000")

# Maps tool names → action_type for the Risk Engine
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
        "ADD_BENEFICIARY": "Customer adding a new beneficiary. Check for social engineering patterns, mule account indicators, and beneficiary policies.",
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
            f"Could you please tell me your Customer ID so I can look you up?"
        )
    elif decision == "ESCALATE":
        return (
            f"I think it's best if a specialist handles this {action_label} for you. "
            f"Let me quickly connect you to a human agent who can assist you further. "
            f"Please hold. Your reference number is {ref_id}."
        )
    else:  # ALLOW
        amt_text = f" of {int(amount):,} rupees" if amount and amount > 0 else ""
        return (
            f"I've gone ahead and processed your {action_label}{amt_text} successfully. "
            f"Your confirmation number is {ref_id}. "
            f"Is there anything else I can help you with today?"
        )


async def _post_evaluation_to_dashboard(evaluation: dict):
    """Post evaluation data to the FastAPI dashboard endpoint (Approach A)."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{FASTAPI_URL}/api/internal/record-evaluation",
                json=evaluation,
                timeout=aiohttp.ClientTimeout(total=3),
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Dashboard POST failed: {resp.status}")
    except Exception as e:
        logger.warning(f"Could not post evaluation to dashboard: {e}")


async def _run_riskpulse_guardrail(
    action_type: str,
    amount: float,
    beneficiary_status: str,
    customer_id: str,
    args: dict,
    verified_customer_id: str | None = None,
) -> str:
    """
    Core RiskPulse pipeline: Moss retrieval → Risk Engine → Decision.
    Returns the spoken response string for the agent to say.
    """
    # Build action
    action = AgentAction(
        action_id=f"LK_{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}",
        customer_id=customer_id,
        action_type=action_type,
        amount=amount,
        beneficiary_status=beneficiary_status,
    )

    # Load customer profile
    customer = load_customer(customer_id)
    if not customer:
        customer = CustomerProfile(
            customer_id=customer_id,
            account_age=0,
            average_transaction_amount=0,
            transaction_frequency=0,
            known_devices=[],
            trusted_beneficiaries=[],
            baseline_risk=30,
        )

    # Build Moss query & search
    query = _build_moss_query(action_type, amount, args)
    context_items, moss_ms = await search_context(query, top_k=5, customer_id=customer_id)

    # Evaluate risk
    risk_decision, eval_ms = evaluate_risk(action, customer, context_items)

    # Post-verification override
    if verified_customer_id and action_type != "VERIFY_IDENTITY":
        risk_decision.decision = "ALLOW"
        risk_decision.explanation = (
            f"Action authorized. Customer {verified_customer_id} identity was verified "
            f"against behavioral history. Original risk score was {risk_decision.risk_score}."
        )
        risk_decision.risk_score = 0

    # For VERIFY_IDENTITY: if behavioral check doesn't hard-block, mark as verified
    if action_type == "VERIFY_IDENTITY" and risk_decision.decision in ("VERIFY", "ALLOW", "ESCALATE"):
        risk_decision.decision = "ALLOW"
        risk_decision.explanation = "Identity successfully verified against behavioral history."

    logger.info(
        f"[RiskPulse] {action_type} -> {risk_decision.decision} | "
        f"Score: {risk_decision.risk_score} | Moss: {moss_ms:.1f}ms | Eval: {eval_ms:.1f}ms"
    )

    # Post to dashboard
    await _post_evaluation_to_dashboard({
        "toolName": action_type.lower(),
        "args": args,
        "decision": risk_decision.decision,
        "score": risk_decision.risk_score,
        "explanation": risk_decision.explanation,
        "moss_ms": round(moss_ms, 1),
        "eval_ms": round(eval_ms, 1),
        "timestamp": datetime.datetime.now().isoformat(),
    })

    # Build spoken response
    spoken = _build_spoken_response(
        action_type, risk_decision.decision, risk_decision.risk_score,
        risk_decision.explanation, amount,
    )

    # If ALLOW and customer has email, send confirmation
    if risk_decision.decision == "ALLOW" and action_type != "VERIFY_IDENTITY":
        if getattr(customer, "email", None):
            send_confirmation_email(customer.email, action_type, amount)

    return spoken, risk_decision


# ─────────────────────────────────────────────────────────────────────
# LiveKit Agent Definition
# ─────────────────────────────────────────────────────────────────────

class RiskPulseAgent(Agent):
    """
    The RiskPulse AI Banking Voice Agent.
    Every banking tool call is intercepted and evaluated through the
    RiskPulse guardrail before execution.
    """

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a professional, friendly, and secure AI banking voice agent for RiskPulse Bank.
You help customers with their banking needs including money transfers, account changes, and other financial operations.

CRITICAL RULES:
1. NEVER mention "risk scores", "RiskPulse", "confidence levels", or "internal security systems" to the customer.
2. Sound conversational, natural, and empathetic.
3. When a customer wants to perform an action, call the appropriate tool.
4. If the customer hasn't verified their identity yet and tries to perform an action, use the verify_identity tool first by asking for their Customer ID.
5. Keep responses concise - 1-3 sentences maximum for voice.
6. Do NOT use any special formatting, emojis, asterisks, or markdown in your responses.
""",
        )
        # Per-session verified customer ID
        self._verified_customer_id: str | None = None

    # ── Banking Tools ──────────────────────────────────────────────
    # Each tool runs through the full RiskPulse pipeline

    @function_tool()
    async def transfer_money(
        self,
        context: RunContext,
        amount: float,
        beneficiary_name: str,
        beneficiary_status: str = "EXISTING",
    ) -> str:
        """Transfer money to a beneficiary. Use this when the customer wants to send or transfer money.

        Args:
            amount: The amount of money to transfer in rupees.
            beneficiary_name: The name of the person receiving the money.
            beneficiary_status: Whether this is a NEW or EXISTING beneficiary.
        """
        context.disallow_interruptions()
        customer_id = self._verified_customer_id or "UNVERIFIED_CALLER"
        args = {"amount": amount, "beneficiary_name": beneficiary_name, "beneficiary_status": beneficiary_status}
        spoken, decision = await _run_riskpulse_guardrail(
            "TRANSFER_MONEY", amount, beneficiary_status, customer_id, args, self._verified_customer_id
        )
        return spoken

    @function_tool()
    async def verify_identity(
        self,
        context: RunContext,
        customer_id: str,
    ) -> str:
        """Verify a customer's identity using their Customer ID. Always call this before processing any banking action.

        Args:
            customer_id: The customer's unique ID, for example C1231006815.
        """
        context.disallow_interruptions()
        args = {"customer_id": customer_id}
        spoken, decision = await _run_riskpulse_guardrail(
            "VERIFY_IDENTITY", 0, "EXISTING", customer_id, args, None
        )
        if decision.decision == "ALLOW":
            self._verified_customer_id = customer_id
        return spoken

    @function_tool()
    async def change_phone_number(
        self,
        context: RunContext,
        new_phone_number: str,
    ) -> str:
        """Change the customer's registered phone number.

        Args:
            new_phone_number: The new phone number to register.
        """
        context.disallow_interruptions()
        customer_id = self._verified_customer_id or "UNVERIFIED_CALLER"
        args = {"new_phone_number": new_phone_number}
        spoken, _ = await _run_riskpulse_guardrail(
            "CHANGE_PHONE", 0, "EXISTING", customer_id, args, self._verified_customer_id
        )
        return spoken

    @function_tool()
    async def change_email(
        self,
        context: RunContext,
        new_email: str,
    ) -> str:
        """Change the customer's registered email address.

        Args:
            new_email: The new email address to register.
        """
        context.disallow_interruptions()
        customer_id = self._verified_customer_id or "UNVERIFIED_CALLER"
        args = {"new_email": new_email}
        spoken, _ = await _run_riskpulse_guardrail(
            "CHANGE_EMAIL", 0, "EXISTING", customer_id, args, self._verified_customer_id
        )
        return spoken

    @function_tool()
    async def process_refund(
        self,
        context: RunContext,
        amount: float,
        reason: str = "",
    ) -> str:
        """Process a refund for the customer.

        Args:
            amount: The refund amount in rupees.
            reason: The reason for the refund.
        """
        context.disallow_interruptions()
        customer_id = self._verified_customer_id or "UNVERIFIED_CALLER"
        args = {"amount": amount, "reason": reason}
        spoken, _ = await _run_riskpulse_guardrail(
            "PROCESS_REFUND", amount, "EXISTING", customer_id, args, self._verified_customer_id
        )
        return spoken

    @function_tool()
    async def add_beneficiary(
        self,
        context: RunContext,
        beneficiary_name: str,
        account_number: str = "",
    ) -> str:
        """Add a new beneficiary to the customer's account.

        Args:
            beneficiary_name: The name of the new beneficiary.
            account_number: The beneficiary's account number.
        """
        context.disallow_interruptions()
        customer_id = self._verified_customer_id or "UNVERIFIED_CALLER"
        args = {"beneficiary_name": beneficiary_name, "account_number": account_number}
        spoken, _ = await _run_riskpulse_guardrail(
            "ADD_BENEFICIARY", 0, "NEW", customer_id, args, self._verified_customer_id
        )
        return spoken

    @function_tool()
    async def reset_pin(self, context: RunContext) -> str:
        """Reset the customer's PIN through the voice channel."""
        context.disallow_interruptions()
        customer_id = self._verified_customer_id or "UNVERIFIED_CALLER"
        args = {}
        spoken, _ = await _run_riskpulse_guardrail(
            "RESET_PIN", 0, "EXISTING", customer_id, args, self._verified_customer_id
        )
        return spoken

    @function_tool()
    async def increase_credit_limit(
        self,
        context: RunContext,
        requested_limit: float,
    ) -> str:
        """Increase the customer's credit limit.

        Args:
            requested_limit: The new credit limit requested in rupees.
        """
        context.disallow_interruptions()
        customer_id = self._verified_customer_id or "UNVERIFIED_CALLER"
        args = {"requested_limit": requested_limit}
        spoken, _ = await _run_riskpulse_guardrail(
            "INCREASE_CREDIT_LIMIT", requested_limit, "EXISTING", customer_id, args, self._verified_customer_id
        )
        return spoken

    @function_tool()
    async def enable_international_transactions(self, context: RunContext) -> str:
        """Enable international transactions on the customer's account."""
        context.disallow_interruptions()
        customer_id = self._verified_customer_id or "UNVERIFIED_CALLER"
        args = {}
        spoken, _ = await _run_riskpulse_guardrail(
            "ENABLE_INTL_TXN", 0, "EXISTING", customer_id, args, self._verified_customer_id
        )
        return spoken

    @function_tool()
    async def close_account(self, context: RunContext) -> str:
        """Close the customer's bank account."""
        context.disallow_interruptions()
        customer_id = self._verified_customer_id or "UNVERIFIED_CALLER"
        args = {}
        spoken, _ = await _run_riskpulse_guardrail(
            "CLOSE_ACCOUNT", 0, "EXISTING", customer_id, args, self._verified_customer_id
        )
        return spoken

    @function_tool()
    async def withdraw_fixed_deposit(
        self,
        context: RunContext,
        amount: float,
    ) -> str:
        """Withdraw from a fixed deposit prematurely.

        Args:
            amount: The amount to withdraw from the fixed deposit in rupees.
        """
        context.disallow_interruptions()
        customer_id = self._verified_customer_id or "UNVERIFIED_CALLER"
        args = {"amount": amount}
        spoken, _ = await _run_riskpulse_guardrail(
            "WITHDRAW_FD", amount, "EXISTING", customer_id, args, self._verified_customer_id
        )
        return spoken


# ─────────────────────────────────────────────────────────────────────
# LiveKit Agent Server Setup
# ─────────────────────────────────────────────────────────────────────

import os
from livekit.plugins import deepgram, openai, silero

async def riskpulse_session(ctx: agents.JobContext):
    """Entry point for each new LiveKit room connection."""
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    session = AgentSession(
        stt=deepgram.STT(),
        llm=openai.LLM(
            model="mistral-small-latest",
            base_url="https://api.mistral.ai/v1",
            api_key=os.getenv("LLM_API_KEY")
        ),
        tts=deepgram.TTS(model="aura-asteria-en"),
    )

    await session.start(
        room=ctx.room,
        agent=RiskPulseAgent(),
    )

    # Greet the user
    await session.generate_reply(
        instructions="Greet the user warmly as a RiskPulse Bank AI assistant. Tell them you can help with transfers, account changes, and other banking operations. Ask how you can assist them today."
    )


if __name__ == "__main__":
    agents.cli.run_app(WorkerOptions(entrypoint_fnc=riskpulse_session))
