# AI Decision Engine — AI Revenue Recovery Platform

---

## Purpose

The AI Decision Engine is the intelligent analysis layer of the recovery workflow. Its role is narrow and clearly bounded:

1. Accept structured context about a failed payment case
2. Diagnose the most likely root cause of the failure
3. Recommend the most appropriate recovery intervention
4. Return a structured, parseable response

The AI engine does **not** execute actions. It does **not** access external APIs. It does **not** access the database during inference. It recommends. The guardrail layer decides. The executor acts.

---

## What AI Does

- Classifies the likely root cause of a payment failure from available signals
- Recommends a specific recovery action from a pre-defined set of allowed actions
- Assigns a confidence level to the recommendation
- Produces a brief natural-language reasoning summary for auditability
- Suggests a timing parameter where relevant (immediate / 24h / 48h)

---

## What AI Does NOT Do

- Execute any payment action
- Call Razorpay or any external payment API
- Send notifications directly
- Access or modify database records
- Override the guardrail / policy engine
- Make irreversible decisions without policy validation
- Operate with unbounded autonomy

---

## Inputs to the AI Engine

The AI engine receives a structured JSON context object assembled by the backend. This context is derived from existing database records and does not require any external API call during inference.

**Context payload (intended schema):**

```json
{
  "case_id": "string — unique recovery case identifier",
  "payment": {
    "id": "string — Razorpay payment ID",
    "amount": "integer — amount in paise",
    "currency": "string — e.g. INR",
    "failure_reason": "string — Razorpay failure reason code",
    "failure_description": "string — human-readable failure description",
    "created_at": "ISO 8601 timestamp",
    "failed_at": "ISO 8601 timestamp"
  },
  "subscription": {
    "id": "string or null",
    "status": "string — e.g. active, halted, cancelled",
    "plan_amount": "integer in paise or null",
    "cycle_number": "integer or null"
  },
  "customer": {
    "id": "string",
    "previous_successful_payments": "integer — count",
    "previous_failed_payments": "integer — count",
    "last_successful_payment_days_ago": "integer or null"
  },
  "recovery_history": {
    "total_attempts_on_this_case": "integer",
    "last_attempt_at": "ISO 8601 timestamp or null",
    "last_attempt_action": "string or null",
    "last_attempt_result": "string or null"
  },
  "merchant_context": {
    "merchant_id": "string",
    "recovery_policy_summary": "string — brief summary of applicable policy constraints"
  }
}
```

The context object is constructed by the backend before invoking the AI engine. Sensitive fields (e.g., card numbers, CVVs, personal identification) are never included.

---

## Structured Output Expected from AI

The AI engine must return a valid JSON object. The backend parses and validates this response before using it. An invalid or incomplete response triggers the fallback path.

**Expected response schema:**

```json
{
  "failure_category": "string — one of: INSUFFICIENT_FUNDS | CARD_EXPIRED | BANK_DECLINED | NETWORK_ERROR | PAYMENT_METHOD_INVALID | CUSTOMER_INITIATED_FAILURE | UNKNOWN",
  "recommended_action": "string — one of: RETRY_PAYMENT | SEND_PAYMENT_LINK | SEND_REMINDER | SCHEDULE_RETRY | ESCALATE_TO_HUMAN | STOP_RECOVERY",
  "confidence": "string — one of: LOW | MEDIUM | HIGH",
  "suggested_timing": "string — one of: IMMEDIATE | AFTER_24H | AFTER_48H | NOT_APPLICABLE",
  "reasoning_summary": "string — max 200 characters, plain language explanation"
}
```

The `recommended_action` field must be one of the six pre-defined action types. The AI is not permitted to recommend arbitrary or free-form actions.

---

## Failure Categories

| Category | Meaning |
|----------|---------|
| `INSUFFICIENT_FUNDS` | Card declined due to insufficient balance |
| `CARD_EXPIRED` | Payment method has expired |
| `BANK_DECLINED` | Bank rejected the transaction without specific reason |
| `NETWORK_ERROR` | Transient network or gateway error |
| `PAYMENT_METHOD_INVALID` | Payment method is invalid or deactivated |
| `CUSTOMER_INITIATED_FAILURE` | Customer declined the charge or initiated a dispute |
| `UNKNOWN` | Failure reason cannot be determined from available data |

---

## Recommended Actions and Their Intended Use

| Action | When appropriate |
|--------|-----------------|
| `RETRY_PAYMENT` | Transient failures (network error, brief bank issue); customer has good payment history |
| `SEND_PAYMENT_LINK` | Card expired, payment method invalid; customer needs to update payment details |
| `SEND_REMINDER` | Payment pending; customer likely unaware |
| `SCHEDULE_RETRY` | Likely temporary issue (insufficient funds at billing date); retry after short delay |
| `ESCALATE_TO_HUMAN` | High-value case, repeated failures, ambiguous situation, low AI confidence |
| `STOP_RECOVERY` | Customer explicitly declined, multiple failed interventions, case has exceeded window |

---

## Decision Factors

The AI engine weighs the following factors when forming its recommendation:

1. **Failure reason code** — primary signal
2. **Amount** — higher amounts warrant more caution and may suggest escalation
3. **Customer payment history** — previously reliable customers with one failure are treated differently from customers with repeated failures
4. **Recovery attempt count** — diminishing returns on repeated retries of the same action type
5. **Time since failure** — recovery window and urgency
6. **Subscription status** — active vs. halted subscriptions have different intervention priorities
7. **Previous intervention results** — if a prior retry failed, recommend a different action type

---

## Confidence Levels

| Level | Meaning |
|-------|---------|
| `HIGH` | Strong signal alignment; the recommended action is clearly appropriate |
| `MEDIUM` | Reasonable recommendation but some ambiguity exists |
| `LOW` | Uncertain diagnosis; escalation should be considered regardless of guardrail outcome |

A `LOW` confidence recommendation will typically trigger escalation at the guardrail layer, but this is enforced by the policy engine — not by the AI itself.

---

## Provider-Agnostic Design

The AI engine is designed to be LLM-agnostic. The implementation will use an interface/adapter pattern:

```
AIEngineInterface
    ├── OpenAIAdapter
    ├── AnthropicAdapter
    ├── GoogleAdapter
    └── [custom adapter]
```

The core recovery workflow depends only on `AIEngineInterface`. Swapping the provider requires only changing the adapter and environment configuration — not the workflow logic.

---

## AI Failure Handling

The AI engine is treated as an unreliable external dependency. The system must remain functional when the AI engine fails.

**Failure modes:**
- LLM provider API timeout or unavailability
- Invalid or unparseable JSON response
- Response contains an unrecognised `recommended_action` value
- Response fails schema validation

**Fallback behavior:**
- Log the failure with full context
- Apply the merchant-level configured fallback action (default: `ESCALATE_TO_HUMAN`)
- Continue the workflow using the fallback action through the standard guardrail → executor path
- Record the AI failure in the audit log

The system does **not** silently swallow AI failures. Every AI failure is audited.

---

## Prompt Engineering (Intended Approach)

The prompt sent to the LLM will:
- Be structured and deterministic (not conversational)
- Include the full context payload as a formatted block
- Explicitly instruct the model to return only valid JSON
- Enumerate the allowed values for `recommended_action`, `failure_category`, `confidence`, and `suggested_timing`
- Instruct the model not to add commentary outside the JSON block

Temperature will be set low (e.g., 0.0) to minimise non-deterministic output.

Prompts are versioned as part of the codebase. Prompt changes are treated as code changes and reviewed accordingly.

---

## What Is Intentionally Not Implemented (MVP)

- Fine-tuned or custom-trained models
- Reinforcement learning from recovery outcomes
- Multi-step reasoning chains (chain-of-thought for production action selection)
- Autonomous agent loops
- Real-time model evaluation during inference
- A/B testing of prompt variants

These may be considered in future phases.
