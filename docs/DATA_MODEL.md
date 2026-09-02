# Data Model — AI Revenue Recovery Platform

---

## Overview

This document describes the intended data model for the platform. These are conceptual entity definitions — no Django models exist yet.

All entities are stored in PostgreSQL. All identifiers are UUIDs unless noted otherwise. Razorpay entity IDs (payment IDs, subscription IDs) are stored as strings alongside internal UUIDs.

---

## Entity Map

```
Merchant ─────────────────────────────────────────────┐
    │                                                  │
    ├─── RecoveryPolicy                                │
    │                                                  │
    ├─── Customer ──── Payment ──── PaymentFailure     │
    │          │                                       │
    │          └──── Subscription ─── PaymentFailure  │
    │                                                  │
    └─── RecoveryCase ──────────────────────────────── ┘
              │
              ├─── AIAnalysis
              │
              ├─── RecoveryDecision
              │
              ├─── RecoveryAction
              │
              ├─── RecoveryResult
              │
              └─── AuditLog
```

---

## Entities

---

### Merchant

Represents a business using the platform.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `name` | String | Business name |
| `razorpay_key_id` | String | Razorpay Key ID for this merchant |
| `razorpay_key_secret` | String (encrypted) | Stored encrypted; never logged |
| `email` | String | Primary contact email |
| `is_active` | Boolean | Soft-disable without deletion |
| `created_at` | Timestamp | |
| `updated_at` | Timestamp | |

**Relationships:**
- Has many `Customer` records
- Has many `Payment` records
- Has one `RecoveryPolicy`

---

### RecoveryPolicy

Merchant-level recovery configuration. Overrides platform defaults within allowed bounds.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `merchant` | FK → Merchant | One policy per merchant |
| `max_retry_attempts` | Integer | Default: 3; platform max: 5 |
| `recovery_window_days` | Integer | Default: 7; platform max: 30 |
| `high_value_threshold_paise` | Integer | Amount above which human approval required |
| `escalation_after_n_failures` | Integer | Default: 2 |
| `fallback_action` | String | Action to use when AI fails; default: ESCALATE_TO_HUMAN |
| `created_at` | Timestamp | |
| `updated_at` | Timestamp | |

---

### Customer

A customer of a merchant. Not a platform user.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `merchant` | FK → Merchant | |
| `razorpay_customer_id` | String | Razorpay customer identifier |
| `name` | String | |
| `email` | String | |
| `phone` | String (optional) | |
| `created_at` | Timestamp | |
| `updated_at` | Timestamp | |

**Relationships:**
- Has many `Payment` records
- Has many `Subscription` records

---

### Payment

A single payment record.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `merchant` | FK → Merchant | |
| `customer` | FK → Customer | |
| `razorpay_payment_id` | String | Razorpay payment identifier |
| `amount_paise` | Integer | Amount in paise (INR) |
| `currency` | String | e.g. INR |
| `status` | String | created / authorized / captured / failed / refunded |
| `description` | String (optional) | |
| `created_at` | Timestamp | When payment was created |
| `updated_at` | Timestamp | |

---

### Subscription

A recurring subscription associated with a customer.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `merchant` | FK → Merchant | |
| `customer` | FK → Customer | |
| `razorpay_subscription_id` | String | Razorpay subscription identifier |
| `plan_id` | String | Razorpay plan identifier |
| `status` | String | created / authenticated / active / pending / halted / cancelled / completed / expired |
| `plan_amount_paise` | Integer | |
| `cycle_number` | Integer | Current billing cycle |
| `current_start` | Timestamp | Current period start |
| `current_end` | Timestamp | Current period end |
| `created_at` | Timestamp | |
| `updated_at` | Timestamp | |

---

### PaymentFailure

A specific failure event tied to a payment or subscription charge.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `payment` | FK → Payment (nullable) | |
| `subscription` | FK → Subscription (nullable) | |
| `merchant` | FK → Merchant | Denormalized for query efficiency |
| `razorpay_error_code` | String | Razorpay error code |
| `razorpay_error_description` | String | Human-readable failure description |
| `razorpay_error_source` | String | bank / gateway / business |
| `razorpay_error_step` | String | payment_authorization / etc. |
| `razorpay_error_reason` | String | Specific reason code |
| `failed_at` | Timestamp | |
| `created_at` | Timestamp | |

At least one of `payment` or `subscription` must be set.

---

### RecoveryCase

The central entity tracking the full lifecycle of a recovery attempt.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `merchant` | FK → Merchant | |
| `payment_failure` | FK → PaymentFailure | |
| `status` | String | State machine (see WORKFLOW.md) |
| `opened_at` | Timestamp | When the case was created |
| `closed_at` | Timestamp (nullable) | When the case was resolved |
| `recovery_window_expires_at` | Timestamp | Calculated from policy + failure time |
| `total_attempts` | Integer | Count of executed recovery actions |
| `created_at` | Timestamp | |
| `updated_at` | Timestamp | |

**Relationships:**
- Has one `AIAnalysis`
- Has many `RecoveryDecision` records (one per evaluation)
- Has many `RecoveryAction` records
- Has one final `RecoveryResult`
- Has many `AuditLog` entries

---

### AIAnalysis

Stores the structured output of the AI Decision Engine for a recovery case.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `recovery_case` | FK → RecoveryCase | |
| `failure_category` | String | AI-classified failure category |
| `recommended_action` | String | AI-recommended action type |
| `confidence` | String | LOW / MEDIUM / HIGH |
| `suggested_timing` | String | IMMEDIATE / AFTER_24H / AFTER_48H / NOT_APPLICABLE |
| `reasoning_summary` | String | Brief AI reasoning (max 200 chars) |
| `raw_prompt` | Text | Full prompt sent to LLM (for audit) |
| `raw_response` | Text | Full LLM response (for audit) |
| `ai_provider` | String | Provider used (e.g., openai) |
| `ai_model` | String | Model version used |
| `ai_call_succeeded` | Boolean | Whether LLM call succeeded |
| `fallback_applied` | Boolean | Whether a fallback action was used |
| `created_at` | Timestamp | |

---

### RecoveryDecision

The policy engine's authorization decision for a proposed action.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `recovery_case` | FK → RecoveryCase | |
| `proposed_action` | String | Action proposed for authorization |
| `authorization_result` | String | APPROVED / REJECTED / ESCALATED |
| `rejection_reason` | String (nullable) | Reason code if REJECTED |
| `rules_triggered` | JSON | List of guardrail rules that were triggered |
| `requires_human_approval` | Boolean | |
| `human_approved_by` | FK → User (nullable) | If human approved |
| `human_approved_at` | Timestamp (nullable) | |
| `created_at` | Timestamp | |

---

### RecoveryAction

An action that was actually executed after authorization.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `recovery_case` | FK → RecoveryCase | |
| `recovery_decision` | FK → RecoveryDecision | Authorization that permitted this action |
| `action_type` | String | Action type executed |
| `execution_status` | String | PENDING / SUCCESS / FAILED |
| `razorpay_reference_id` | String (nullable) | e.g., payment link ID or retry payment ID |
| `executed_at` | Timestamp | |
| `execution_error` | String (nullable) | Error details if execution failed |
| `created_at` | Timestamp | |

---

### RecoveryResult

The outcome of a recovery case after action execution.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `recovery_case` | FK → RecoveryCase | One per case |
| `recovery_action` | FK → RecoveryAction | The action that produced this result |
| `result_status` | String | RECOVERED / FAILED / ESCALATED / STOPPED / PENDING |
| `recovered_amount_paise` | Integer (nullable) | Actual amount recovered; null if not recovered |
| `razorpay_payment_id` | String (nullable) | If recovery payment occurred |
| `result_confirmed_at` | Timestamp (nullable) | When outcome was confirmed |
| `created_at` | Timestamp | |

---

### AuditLog

Append-only record of every event in the recovery workflow.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `recovery_case` | FK → RecoveryCase (nullable) | |
| `merchant` | FK → Merchant | |
| `stage` | String | DETECT / DIAGNOSE / DECIDE / GUARD / ACT / RECOVER / MEASURE / AUDIT |
| `event_type` | String | e.g., CASE_OPENED / AI_CALLED / GUARDRAIL_EVALUATED / ACTION_EXECUTED / etc. |
| `actor` | String | system / ai_engine / policy_engine / executor / human:{user_id} |
| `description` | Text | Human-readable description of the event |
| `metadata` | JSON | Additional context (redacted of sensitive fields) |
| `created_at` | Timestamp | Set at insert; never updated |

The `AuditLog` table is append-only. No row is ever updated or deleted.

---

## Key Relationships Summary

| Relationship | Cardinality |
|--------------|-------------|
| Merchant → RecoveryPolicy | 1:1 |
| Merchant → Customer | 1:many |
| Customer → Payment | 1:many |
| Customer → Subscription | 1:many |
| Payment → PaymentFailure | 1:1 (typically) |
| Subscription → PaymentFailure | 1:many |
| PaymentFailure → RecoveryCase | 1:1 |
| RecoveryCase → AIAnalysis | 1:many (re-diagnosis on new attempt) |
| RecoveryCase → RecoveryDecision | 1:many |
| RecoveryCase → RecoveryAction | 1:many |
| RecoveryCase → RecoveryResult | 1:1 (final outcome) |
| RecoveryCase → AuditLog | 1:many |

---

## Notes on Sensitive Data

- Razorpay API secrets are stored encrypted in the `Merchant` model and never logged
- Card numbers, CVVs, and bank account details are never stored
- Customer PII (name, email, phone) is stored for operational purposes only
- Audit logs exclude sensitive fields; they record event context, not raw payment data
