# Guardrails and Policy Engine — AI Revenue Recovery Platform

---

## Purpose

The Guardrail / Policy Engine is the deterministic authorization layer that sits between the AI Decision Engine and the Action Executor. Its purpose is to ensure that no AI recommendation is executed unless it has been explicitly validated against applicable policies.

This layer is non-negotiable. It cannot be bypassed by the AI engine, the frontend, or any other component. Every action — without exception — must pass through this layer before execution.

**Core principle:** The AI can recommend. The policy engine decides. The executor only acts on an authorization.

---

## Why Deterministic Guardrails Are Essential

AI systems are probabilistic. They can recommend suboptimal actions, misclassify failure causes, or behave unexpectedly on edge cases. In a payment recovery context, an incorrect action can:

- Annoy or damage the relationship with a customer
- Create duplicate charges
- Exceed legally or contractually appropriate retry limits
- Expose the merchant to chargeback risk
- Create audit and compliance gaps

Deterministic guardrails make the system's behavior predictable, auditable, and safe — regardless of AI output quality.

---

## Policy Engine: Authorization Flow

```
AI Recommendation received
        │
        ▼
[Rule 1] Retry limit check
        │
        ▼
[Rule 2] Recovery window check
        │
        ▼
[Rule 3] Duplicate action check
        │
        ▼
[Rule 4] Amount threshold check
        │
        ▼
[Rule 5] Escalation threshold check
        │
        ▼
[Rule 6] Stopping rule check
        │
        ▼
Authorization Decision: APPROVED | REJECTED | ESCALATED
```

Rules are evaluated in order. If any rule triggers a REJECTED or ESCALATED outcome, evaluation stops and the result is returned immediately.

---

## Rules

### Rule 1: Retry Limit

**What it checks:** The total number of `RETRY_PAYMENT` or `SCHEDULE_RETRY` actions already executed on this recovery case.

**Policy:** A recovery case may not exceed the configured maximum retry attempts (default: 3, configurable per merchant between 1 and 5).

**If triggered:**
- If the recommended action is `RETRY_PAYMENT` or `SCHEDULE_RETRY`, the action is changed to `ESCALATE_TO_HUMAN` or `STOP_RECOVERY` depending on merchant configuration.
- Authorization result: ESCALATED or REJECTED.

---

### Rule 2: Recovery Window

**What it checks:** The time elapsed since the original payment failure.

**Policy:** Recovery may only be attempted within the configured recovery window (default: 7 days, configurable per merchant between 1 and 30 days).

**If triggered:**
- No further recovery actions are authorized.
- The case is closed.
- Authorization result: REJECTED (reason: `RECOVERY_WINDOW_EXPIRED`).

---

### Rule 3: Duplicate Action Prevention

**What it checks:** Whether the same action type was already executed on this case within a minimum time window (default: 24 hours).

**Policy:** The same action type cannot be executed twice within the minimum time window.

**If triggered:**
- Authorization result: REJECTED (reason: `DUPLICATE_ACTION_PREVENTED`).
- The system records the prevention in the audit log.

---

### Rule 4: Amount Threshold

**What it checks:** The payment amount against configured thresholds.

**Policy:**
- Payments above the high-value threshold (configurable per merchant; default: INR 500 in paise = 50000 paise) automatically trigger escalation for human review before execution.
- The AI recommendation is preserved but marked as requiring human approval.

**If triggered:**
- Authorization result: ESCALATED (reason: `HIGH_VALUE_REQUIRES_APPROVAL`).

---

### Rule 5: Escalation Threshold

**What it checks:** The number of previously failed recovery attempts on this case (regardless of action type).

**Policy:** If the number of failed recovery attempts reaches the escalation threshold (default: 2), the case must be escalated to a human operator regardless of the AI recommendation.

**If triggered:**
- Authorization result: ESCALATED (reason: `REPEATED_FAILURE_ESCALATION`).

---

### Rule 6: Stopping Rules

**What it checks:** Specific conditions that indicate recovery should cease.

**Stopping conditions:**
- Customer has explicitly declined the charge or initiated a dispute
- Payment method has been permanently invalidated (e.g., card permanently blocked)
- Case has been in `PENDING_RESULT` for longer than the abandonment timeout (default: 14 days)
- Merchant has manually flagged the case as do-not-recover
- The AI has recommended `STOP_RECOVERY` AND the guardrail concurs based on case history

**If triggered:**
- Authorization result: REJECTED (reason: `STOPPING_RULE_TRIGGERED`).
- A `STOP_RECOVERY` action is recorded and the case is closed.

---

## Human Approval Flow

When a case is ESCALATED, it is routed to a human operator queue. The human operator may:

1. **Approve the original AI recommendation** — the action proceeds through the executor
2. **Approve a different action** — the human selects an alternative from the allowed action set
3. **Close the case without action** — the case is marked as resolved by human decision

Human approvals are recorded in the audit log with operator identity and timestamp. A human operator cannot execute an action outside the allowed action set.

---

## Policy Configuration

Recovery policies are configured at two levels:

| Level | Scope |
|-------|-------|
| Platform defaults | Applied to all merchants unless overridden |
| Merchant-level policy | Overrides platform defaults within allowed ranges |

Merchants cannot set policies that exceed platform safety bounds. For example:
- Maximum retries cannot exceed 5 (platform hard limit)
- Recovery window cannot exceed 30 days (platform hard limit)

Policy configuration is stored in the `RecoveryPolicy` data model (see [`DATA_MODEL.md`](DATA_MODEL.md)).

---

## Audit Requirements

Every guardrail evaluation produces an audit record containing:
- Case ID
- Timestamp
- Rule(s) evaluated
- Rule(s) triggered (if any)
- Authorization result
- Reason code
- Resulting action (approved, rejected, or escalated)

No guardrail decision is made without an audit trail entry.

---

## Action Authorization Summary

| Action Type | Guardrail Behavior |
|-------------|-------------------|
| `RETRY_PAYMENT` | Checked against retry limit, recovery window, duplicate prevention |
| `SEND_PAYMENT_LINK` | Checked against recovery window, duplicate prevention |
| `SEND_REMINDER` | Checked against duplicate prevention (lower cooldown) |
| `SCHEDULE_RETRY` | Checked against retry limit, recovery window |
| `ESCALATE_TO_HUMAN` | Almost always approved; checked against duplicate escalation prevention |
| `STOP_RECOVERY` | Always approved; no further actions will be authorized on the case |

---

## Graceful Failure in the Policy Engine

If the policy engine itself encounters an error (e.g., database unavailability when checking retry count):

- The action is blocked (fail-safe: do nothing)
- The error is logged to the audit trail
- The case is flagged for manual review
- No action is executed

The policy engine fails safe. It does not fail open.

---

## What Is Intentionally Not Implemented (MVP)

- Machine learning-based policy optimization
- Real-time policy updates without restart
- Per-customer-level policy overrides
- Complex multi-rule interaction modeling
- Regulatory compliance policy modules (PCI DSS, RBI, etc.)

These are future-phase concerns.
