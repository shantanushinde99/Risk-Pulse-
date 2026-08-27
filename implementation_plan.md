# Enterprise Security Upgrade (Removing Shortcuts)

I completely understand. If this code is going before judges, it needs to be bulletproof, logically sound, and completely free of "hackathon magic." 

We will remove the hardcoded `CUST_DEMO_ATO` and the fake mock profiles. We will implement a mathematically sound, enterprise-grade authentication flow.

## Open Questions
Before I execute this, I want to clarify how an "unknown" caller should be handled. In a real bank, if the AI doesn't know who is calling, it *cannot* approve a transaction. 
My plan is to make the system **secure by default**. If a caller tries to make a transfer and the system doesn't have their `customer_id` yet, it will automatically trigger the `VERIFY` flow, forcing them to type their ID into the chat box. Is this acceptable?

## Proposed Changes

### `backend/app/main.py`
We will implement real **Call-based Session Management** and remove mock data generation.

#### [MODIFY] main.py
- **Remove Global `IS_VERIFIED` Hack**: Delete the global boolean.
- **Implement Session Memory**: Create a `call_sessions` dictionary mapped to VAPI's unique `call_id`. When a user connects, their session is tracked legitimately.
- **Remove `CUST_DEMO_ATO`**: The system will no longer assume the caller is `CUST_DEMO_ATO`. Instead, the `customer_id` will default to `None`.
- **Remove Mock Profile Generation**: Delete the fallback block that invents a fake `CustomerProfile`. If an ID is provided but doesn't exist in our actual CSV database, the system will instantly `BLOCK` the transaction as an invalid account.
- **Update Webhook Logic**: 
  - Extract `call_id` from the VAPI payload.
  - If a tool is called (e.g. `transfer_money`) and `call_id` has no associated `customer_id` in the session, the system will instantly return a `VERIFY` decision. (Secure by default).
  - When the user types their ID and triggers `verify_identity`, the backend will save that real ID into `call_sessions[call_id]`.
  - When VAPI automatically re-triggers `transfer_money`, the backend will retrieve the real ID from the session, query the Moss vector DB for *that specific user*, and run the Risk Engine legitimately.

## Verification Plan
### Automated / Manual Testing
1. Start a call.
2. Ask to transfer money.
3. The system should recognize you are unknown (No session) and force a `VERIFY` challenge.
4. Type a real ID from the PaySim dataset (e.g., `C1231006815`) into the chat box.
5. The system will verify you, store your session, and process the transfer automatically using your real behavioral data from Moss.
6. Try typing a fake ID (e.g., `FAKE123`). The system should legitimately `BLOCK` you since the account doesn't exist.
