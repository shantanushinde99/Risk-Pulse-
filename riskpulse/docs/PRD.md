# Product Requirements Document (PRD): RiskPulse

## 1. Product Overview
**Product Name:** RiskPulse
**Tagline:** Zero-Latency Contextual Risk and Safety Layer for AI Agents
**Target Audience:** Fintech companies, digital banks, and enterprise businesses utilizing AI voice/chat agents for customer support and transactional workflows.

### 1.1 Problem Statement
As banks adopt LLM-driven Voice and Chat agents (e.g., VAPI) to handle customer support, these agents are increasingly granted access to transactional APIs (transferring money, resetting PINs). However, LLMs lack the ability to holistically evaluate the deep, historical context of a user before executing a tool call. If an attacker bypasses the LLM's prompt, the LLM will happily execute a fraudulent transaction. Traditional fraud systems exist, but they are often async, high-latency, and disconnected from the conversational flow, leading to terrible UX.

### 1.2 The Solution
RiskPulse acts as a deterministic, ultra-fast interception layer (guardrail) sitting exactly between the AI Agent and the Execution APIs. Before any tool is executed, RiskPulse intercepts the payload and semantically queries a vector database (Moss) containing tens of thousands of security policies, historical fraud cases, and customer timelines. It generates a Risk Score in under 10ms, blocking malicious actions before they hit the bank's APIs, and returns a safe explanation to the AI agent so the conversation continues naturally.

---

## 2. Key Features & Requirements

### 2.1 Sub-10ms Contextual Retrieval
* **Requirement:** The system must be capable of retrieving relevant context from a massive dataset (50,000+ records) instantly without bottlenecking the voice conversation.
* **Implementation:** Utilize the **Moss Vector Database** to index synthetic PaySim data, historical fraud cases, and textual security policies for lightning-fast semantic retrieval.

### 2.2 Deterministic Risk Engine
* **Requirement:** The system must not rely solely on an LLM to decide if an action is safe, as LLMs can hallucinate or be prompt-injected.
* **Implementation:** A Python-based deterministic engine that takes the semantic context retrieved from Moss and calculates a rigid `Risk Score` (0-100) based on weighted factors (Amount, Customer Baseline Risk, Beneficiary Status).

### 2.3 Real-time Interception & Telemetry UI
* **Requirement:** Security operations teams need to see what the AI agents are doing in real-time.
* **Implementation:** A Next.js dashboard featuring a `Threat Vector Simulator` and an `Interactive Risk Sandbox` that visualizes the AI agent's tool calls, the Moss latency, the retrieved context, and the final decision in real-time.

### 2.4 VAPI Voice Agent Integration
* **Requirement:** Must natively support interception of Voice AI tool calls.
* **Implementation:** Expose a FastAPI webhook that VAPI can hit during a `tool_call`. The webhook evaluates the risk and returns the decision directly into the WebRTC voice stream.

---

## 3. User Flows

### 3.1 The Hackathon Demo Flow (Risk Sandbox)
1. The judge opens the Next.js Dashboard.
2. The judge uses the **Risk Sandbox** sliders to simulate a high-risk transaction (e.g., $100,000 to a New Beneficiary with a high Customer Baseline Risk).
3. The judge clicks **Inject Payload**.
4. The dashboard displays the payload traveling to the backend.
5. The **Moss Context** panel populates with 5 relevant security policies retrieved in under 10ms from a database of 50,000+ records.
6. The **Risk Evaluation Engine** panel visually blocks the transaction, displaying a Risk Score of 95.

### 3.2 The Voice Agent Flow
1. The user calls the VAPI voice agent and says: *"I lost my card, I need to reset my PIN."*
2. The agent attempts to call the `reset_pin` tool.
3. RiskPulse intercepts the webhook, queries Moss, and determines the action is safe (Risk Score: 15).
4. RiskPulse returns `status: ALLOW` to VAPI.
5. The Voice agent says: *"I have successfully reset your PIN, is there anything else I can help you with?"*

---

## 4. Technical Architecture
* **Frontend UI:** Next.js 14, TailwindCSS, Framer Motion
* **Backend API:** FastAPI (Python), Uvicorn
* **Semantic Engine:** Moss Vector Database (Indexing 50,173 synthetic PaySim records)
* **LLM Layer:** Mistral AI (For explaining the block/allow decisions)
* **Voice Agent:** VAPI (WebRTC audio streaming and function calling)

---

## 5. Success Metrics (Hackathon Evaluation)
* **Performance:** Moss semantic retrieval latency must consistently remain under 15ms during live demos.
* **Reliability:** The Voice Agent must never drop a call due to a webhook timeout.
* **UX/UI:** The dashboard must look like a premium, cyberpunk-themed security terminal, wowing the judges.
* **Scale:** Successfully prove that the system is querying against a massive dataset (50,000+ PaySim records) rather than a hardcoded array of 5 rules.

---

## 6. Future Roadmap (Post-Hackathon)
1. **Multi-Agent Support:** Allow RiskPulse to act as a central security router for swarms of AI agents.
2. **Dynamic Policy Updates:** Build a UI for security engineers to type new policies in plain English and have them instantly embedded into Moss.
3. **Graph-based Risk:** Integrate a Graph Database to analyze multi-hop money laundering networks in conjunction with Moss semantic search.
