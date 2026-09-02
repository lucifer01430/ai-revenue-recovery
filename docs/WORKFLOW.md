# Recovery Workflow — AI Revenue Recovery Platform

---

## Overview

The recovery workflow is the core operational loop of the platform. Every failed payment or lapsed subscription is processed through a structured sequence of eight stages:

```
DETECT → DIAGNOSE → DECIDE → GUARD → ACT → RECOVER → MEASURE → AUDIT
```

Each stage has a defined input, a defined output, and a defined failure mode. The stages are not optional — every recovery case passes through all of them, even if some transitions are immediate (e.g., a GUARD rejection moves directly to AUDIT without reaching ACT).

---

## Stage Definitions

### 1. DETECT

**Input:** Payment failure event, subscription status change, or scheduled detection scan  
**Output:** A new `RecoveryCase` record with status `DETECTED`

The detection layer identifies:
- Payments that have failed (status: `failed`)
- Subscriptions that have lapsed or failed to charge
- Payments that have been pending beyond an acceptable threshold
- Repeated failures on the same customer/merchant combination

Detection sources:
- Razorpay webhooks (payment failure events)
- Periodic polling of Razorpay payment/subscription APIs
- Manual ingestion (for evaluation and testing)

A `PaymentFailure` record is created capturing the raw failure data. A `RecoveryCase` is opened to track the full lifecycle. Duplicate detection prevents the same payment failure from opening multiple cases.

---

### 2. DIAGNOSE

**Input:** `RecoveryCase` with raw payment failure data  
**Output:** `AIAnalysis` record with structured diagnosis

The AI Decision Engine receives a structured context payload including:
- Payment failure reason code (e.g., `insufficient_funds`, `card_expired`, `bank_declined`)
- Payment amount
- Customer payment history (previous failures, previous successful payments)
- Subscription status (active, paused, cancelled)
- Number of previous recovery attempts on this case
- Time since original failure
- Merchant-level context

The AI produces a structured JSON output:
- `failure_category`: classification of the likely root cause
- `recommended_action`: one of the defined action types
- `confidence`: LOW / MEDIUM / HIGH
- `reasoning_summary`: a brief natural-language explanation
- `suggested_timing`: when the action should occur (e.g., immediate, 24h, 48h)

If the AI call fails or returns an invalid response, the case falls back to a configurable safe default action (typically `ESCALATE_TO_HUMAN`).

---

### 3. DECIDE

**Input:** `AIAnalysis` structured output  
**Output:** Proposed `RecoveryDecision` record (pending guardrail validation)

The recovery decision is formed from the AI analysis:
- Selected action type
- Target timing
- Confidence level
- Reasoning

At this stage, the decision is proposed but not yet authorized. It proceeds to the guardrail layer.

---

### 4. GUARD

**Input:** Proposed `RecoveryDecision`  
**Output:** Authorization result: `APPROVED`, `REJECTED`, or `ESCALATED`

The deterministic policy engine validates the proposed decision against applicable rules:

- **Retry limit check:** Has this payment/subscription exceeded the maximum allowed retry attempts?
- **Recovery window check:** Is this case still within the merchant's defined recovery window?
- **Duplicate action check:** Was this same action attempted recently on this case?
- **Amount threshold check:** Does the amount require additional authorization or escalation?
- **Stopping rule check:** Has a stopping condition been triggered (e.g., customer explicitly declined, payment method invalid with no alternative)?
- **Escalation threshold check:** Has the number of failed interventions on this case reached the escalation threshold?

**APPROVED:** The recommended action is authorized. Execution may proceed.  
**REJECTED:** The action is not authorized. The case is closed or placed in a holding state.  
**ESCALATED:** The case exceeds automated recovery scope. It is routed to human review.

The guardrail layer records its decision and reasoning in the `RecoveryDecision` record.

---

### 5. ACT

**Input:** Authorized `RecoveryDecision`  
**Output:** `RecoveryAction` record with execution status

The Action Executor performs the approved action:

| Action Type | Execution |
|-------------|-----------|
| `RETRY_PAYMENT` | Calls Razorpay API to trigger payment retry |
| `SEND_PAYMENT_LINK` | Generates Razorpay payment link; sends via notification |
| `SEND_REMINDER` | Sends a payment reminder (email at MVP stage) |
| `SCHEDULE_RETRY` | Creates a scheduled job for future retry execution |
| `ESCALATE_TO_HUMAN` | Creates an escalation record; notifies operator |
| `STOP_RECOVERY` | Closes the case; no further actions taken |

Execution is idempotent: a duplicate execution request for the same case+action+window will not produce a duplicate external call.

If the action execution fails (e.g., Razorpay API error), the failure is recorded and the case moves to an error state. No retry of the recovery action itself is made automatically — this prevents compounding failures.

---

### 6. RECOVER

**Input:** Executed `RecoveryAction`  
**Output:** `RecoveryResult` record

After an action is executed, the platform tracks the payment outcome:

- Razorpay webhook confirms payment success → `RECOVERED`
- Razorpay webhook confirms payment failure → `FAILED`
- No webhook received within timeout → `PENDING` (scheduled follow-up check)
- Case was escalated → `ESCALATED`
- Case was stopped → `STOPPED`

The `RecoveryResult` records the final payment status and the amount recovered (if any).

---

### 7. MEASURE

**Input:** Aggregated `RecoveryResult` records  
**Output:** Analytics metrics

Metrics are computed on demand from actual records in the database:

- Total revenue at risk (sum of amounts in active recovery cases)
- Total revenue recovered (sum of amounts with result `RECOVERED`)
- Recovery rate (recovered / total at risk)
- Breakdown by failure reason
- Breakdown by action type
- Escalated case count
- Stopped case count
- Average recovery time
- AI confidence distribution

No metrics are hardcoded. All values reflect real records.

---

### 8. AUDIT

**Input:** All steps above  
**Output:** Append-only `AuditLog` entries

Every transition in the workflow writes an audit log entry containing:
- Timestamp
- Stage name
- Case ID
- Actor (system, AI engine, policy engine, executor, human operator)
- Action or decision taken
- Reasoning or notes
- Result

Audit logs are never modified after creation. They form the complete, traceable history of every recovery case.

---

## Flow Diagrams

### Normal Recovery Flow (Payment Recovered)

```mermaid
flowchart TD
    A[Payment fails] --> B[DETECT\nCreate PaymentFailure + RecoveryCase]
    B --> C[DIAGNOSE\nAI analyzes failure context]
    C --> D[DECIDE\nAI proposes recovery action]
    D --> E[GUARD\nPolicy engine validates]
    E -->|APPROVED| F[ACT\nExecute recovery action]
    F --> G[RECOVER\nTrack payment outcome]
    G -->|Payment succeeded| H[MEASURE\nUpdate analytics]
    H --> I[AUDIT\nLog complete trail]
    I --> J([Case closed — RECOVERED])
```

---

### Failed Recovery Flow (Payment Still Fails)

```mermaid
flowchart TD
    A[Action executed] --> B[RECOVER\nTrack payment outcome]
    B -->|Payment failed again| C{Retry limit\nreached?}
    C -->|No| D[Re-enter DIAGNOSE\nfor next attempt]
    C -->|Yes| E[GUARD\nStopping rule triggered]
    E --> F[STOP_RECOVERY action]
    F --> G[AUDIT\nLog stopped case]
    G --> H([Case closed — STOPPED])
```

---

### Escalation Flow

```mermaid
flowchart TD
    A[GUARD evaluation] -->|ESCALATED| B[ACT\nCreate escalation record]
    B --> C[Notify human operator]
    C --> D{Human decision}
    D -->|Approve action| E[Execute action manually\nor override guardrail]
    D -->|Close case| F[Close as unresolved]
    E --> G[AUDIT\nLog human decision]
    F --> G
    G --> H([Case closed — ESCALATED])
```

---

### Stopping Flow

```mermaid
flowchart TD
    A[GUARD evaluation] -->|Stopping rule triggered| B[RecoveryDecision\nREJECTED]
    B --> C[ACT\nExecute STOP_RECOVERY]
    C --> D[AUDIT\nLog stopping reason]
    D --> E([Case closed — STOPPED])
```

---

### Graceful Failure Flow (AI Engine Failure)

```mermaid
flowchart TD
    A[DIAGNOSE\nAI call initiated] --> B{AI call\nsucceeded?}
    B -->|Yes| C[Parse and validate AI response]
    C --> D{Response\nvalid?}
    D -->|Yes| E[Proceed to DECIDE]
    D -->|No — invalid response| F[Log AI failure]
    B -->|No — API error / timeout| F
    F --> G[Apply safe fallback action\ne.g. ESCALATE_TO_HUMAN]
    G --> H[GUARD\nValidate fallback action]
    H --> I[ACT\nExecute fallback]
    I --> J[AUDIT\nLog AI failure and fallback]
```

---

## State Machine Summary

| State | Description |
|-------|-------------|
| `DETECTED` | Failure identified; case opened |
| `DIAGNOSING` | AI analysis in progress |
| `DECIDING` | Decision proposed; awaiting guardrail |
| `APPROVED` | Action authorized by policy engine |
| `REJECTED` | Action rejected by policy engine |
| `ESCALATED` | Case routed to human operator |
| `ACTING` | Recovery action being executed |
| `PENDING_RESULT` | Action executed; awaiting payment outcome |
| `RECOVERED` | Payment succeeded after intervention |
| `FAILED` | Payment failed despite intervention |
| `STOPPED` | Recovery ceased per stopping rules |
| `ERROR` | Unrecoverable system error; case flagged for review |
