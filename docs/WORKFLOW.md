# System Workflow

The AI Revenue Recovery Platform follows a strict, sequential workflow: 
`DETECT` → `DIAGNOSE` → `DECIDE` → `GUARD` → `ACT` → `RECOVER` → `MEASURE` → `AUDIT`

## Core Data Flow

### 1. DETECT (Ingress)
- A webhook from Razorpay (`payment.failed`) hits the `payments` app.
- The system normalizes the payload into a `PaymentEvent`.
- If the event is a failure, a `RecoveryCase` is created and marked as `OPEN`.

### 2. DIAGNOSE & 3. DECIDE (AI Flow)
- The `recovery` orchestrator packages the case context (failure reason, customer history, amount).
- This context is sent to the `intelligence` app.
- The AI Provider (LLM) evaluates the context and returns a structured JSON response containing:
  - **Diagnosis**: The likely root cause (e.g., "Insufficient funds").
  - **Decision/Recommendation**: The proposed action (e.g., "Wait 2 days and retry").
- The recommendation is temporarily attached to the `RecoveryCase`.

### 4. GUARD (Guardrail Flow)
- The `AIRecommendation` is passed to the `guardrails` app.
- The deterministic engine evaluates the recommendation against business rules.
- **Scenario A (Pass)**: The action is within limits. It is marked as `APPROVED`.
- **Scenario B (Block/Modify)**: The AI recommended a 4th retry, but the policy limit is 3. The guardrail intercepts it, creates a `GuardrailIntervention` record, and changes the action to `ESCALATE` or `STOP`.

### 5. ACT (Execution Boundary)
- Only `APPROVED` actions reach the execution phase.
- The `recovery` app translates the action into a concrete command (e.g., calling the Razorpay API to retry a payment).
- The action is executed.

### 6. RECOVER (Outcome)
- The system listens for the outcome of the action (e.g., another webhook indicating success or failure).
- If successful, the `RecoveryCase` is marked as `RECOVERED`.
- If failed, the workflow may loop back to DIAGNOSE (if retries remain) or mark the case as `FAILED`.

### 7. MEASURE
- The system aggregates outcomes. It calculates actual revenue recovered based on `RECOVERED` cases, rather than theoretical metrics.

### 8. AUDIT (Continuous)
- Throughout the entire workflow, the `audit` app logs every transition.
- When the case is created, when the AI makes a recommendation, when the guardrail intervenes, and when the final action executes, an immutable `AuditLog` entry is written.

## AI Decision & Guardrail Separation

The most critical architectural boundary is between the AI and the Guardrails.
- **AI is an Advisor**: It provides context-aware suggestions but has no execution authority.
- **Guardrails are the Enforcer**: They are simple, deterministic python functions (e.g., `if retries >= MAX_RETRIES: block()`).
- **No Direct Execution**: The AI never holds API keys to the payment gateway.
