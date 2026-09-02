# Razorpay Integration Plan — AI Revenue Recovery Platform

---

## Overview

Razorpay is the primary payment infrastructure for this platform. All integration will use **Razorpay Test Mode** during development and evaluation. No real money is processed at any stage of the MVP.

The integration is intentionally scoped to the features needed for the recovery workflow. We are not building a full payment gateway integration.

---

## Test Mode Commitment

- All Razorpay API calls use Test Mode credentials (`rzp_test_*` key IDs)
- Test Mode provides a realistic API surface without real transactions
- Test Mode payment IDs, subscription IDs, and customer IDs follow the same schema as production
- Test Mode supports webhook simulation for payment success/failure events

**No production Razorpay credentials will be used at any stage of the MVP.**

---

## Credentials and Security

- Razorpay Key ID and Key Secret are stored as environment variables (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`)
- Secrets are never committed to version control
- The `.env.example` file contains placeholder values only
- Webhook secret is stored separately (`RAZORPAY_WEBHOOK_SECRET`) for signature verification
- Per-merchant Razorpay keys (if multi-merchant is implemented) are stored encrypted in the database

See [`SECURITY.md`](SECURITY.md) for the full secrets management approach.

---

## Planned Integration Points

### 1. Payment Data Ingestion

**Purpose:** Retrieve payment records to populate the platform's database for analysis.

**Approach:**
- Use the Razorpay Payments API to fetch payment records by status (failed, pending)
- Filter for failure events relevant to the current merchant
- Store raw payment data in the `Payment` and `PaymentFailure` models

**Relevant Razorpay API:** `GET /v1/payments` with appropriate filters

**Important fields captured:**
- `id` (Razorpay payment ID)
- `amount` (in paise)
- `currency`
- `status`
- `error_code`
- `error_description`
- `error_source`
- `error_step`
- `error_reason`
- `created_at`

---

### 2. Subscription Data Ingestion

**Purpose:** Retrieve subscription records to detect halted or failed subscriptions.

**Relevant Razorpay API:** `GET /v1/subscriptions` with `status=halted` or `status=pending`

**Important fields captured:**
- `id` (Razorpay subscription ID)
- `plan_id`
- `status`
- `current_start`
- `current_end`
- `charge_at`
- `total_count`
- `paid_count`
- `remaining_count`

---

### 3. Customer Data

**Purpose:** Retrieve customer details associated with failed payments.

**Relevant Razorpay API:** `GET /v1/customers/{id}`

**Note:** Customer data is fetched on demand during detection — not bulk-imported.

---

### 4. Payment Retry

**Purpose:** Trigger a retry of a failed payment where supported.

**Approach:**
- Razorpay does not directly expose a generic "retry payment" endpoint for arbitrary failed payments
- For subscription-linked failures: use subscription charge/retry APIs where applicable
- For standalone payment retries: generate a new payment link for the customer to complete payment

**Relevant Razorpay API (subscription retry):** `POST /v1/subscriptions/{id}/charge`

**Important:** The retry action is only executed after receiving authorization from the guardrail engine. An idempotency key is generated per attempt to prevent duplicate charges.

---

### 5. Payment Link Generation

**Purpose:** Generate a Razorpay Payment Link that the customer can use to complete payment with a different method.

**Relevant Razorpay API:** `POST /v1/payment_links`

**Payload (intended):**
```json
{
  "amount": "<amount in paise>",
  "currency": "INR",
  "description": "Payment recovery link",
  "customer": {
    "name": "<customer name>",
    "email": "<customer email>"
  },
  "notify": {
    "sms": false,
    "email": true
  },
  "callback_url": "<platform callback URL>",
  "callback_method": "get",
  "reference_id": "<recovery_action_id>"
}
```

The `reference_id` is set to the `RecoveryAction.id` for traceability.

---

### 6. Webhooks

**Purpose:** Receive real-time payment outcome notifications from Razorpay.

**Relevant events:**
- `payment.captured` — payment succeeded
- `payment.failed` — payment failed
- `subscription.charged` — subscription charge succeeded
- `subscription.halted` — subscription charge failed repeatedly
- `payment_link.paid` — payment link was completed by customer

**Security:**
- All webhook payloads are verified using HMAC-SHA256 signature with `RAZORPAY_WEBHOOK_SECRET`
- Invalid signatures are rejected with HTTP 400 and logged
- Webhook events are idempotent: processing the same event twice produces the same outcome

**Webhook endpoint:** `POST /webhooks/razorpay/`

---

### 7. Idempotency

Every write operation to the Razorpay API uses an idempotency key. This prevents:
- Duplicate payment retries
- Duplicate payment link creation
- Duplicate charges on the same subscription cycle

The idempotency key is derived from the `RecoveryAction.id` and the action type, ensuring uniqueness per action attempt.

---

## Razorpay API Error Handling

Razorpay API calls can fail for various reasons: network errors, rate limits, invalid parameters, or authentication failures. The platform handles these as follows:

| Error Type | Handling |
|------------|---------|
| Network timeout | Log error; mark RecoveryAction as FAILED; audit case |
| Rate limit (429) | Log error; schedule delayed retry of the API call (not the payment) |
| Authentication failure (401) | Alert; mark merchant credentials as invalid; suspend recovery for merchant |
| Bad request (400) | Log full request/response; mark action as FAILED; audit case |
| Razorpay server error (5xx) | Log error; treat as transient; schedule follow-up check |

No Razorpay API error causes an unhandled exception that halts the system. All errors are logged and audited.

---

## Integration Scope Boundaries

**In scope for MVP:**
- Razorpay Test Mode only
- Payment data ingestion
- Subscription data ingestion
- Payment retry (subscription-linked)
- Payment link generation
- Webhook handling for payment outcomes
- Idempotency on all write operations

**Explicitly out of scope for MVP:**
- Razorpay Production Mode integration
- Razorpay X (banking) features
- UPI integration
- International payment methods
- Razorpay Smart Collect
- Razorpay Route (splits/transfers)
- Razorpay Checkout frontend embed
- Razorpay Magic Checkout

---

## Testing in Test Mode

Razorpay Test Mode provides test card numbers and UPI IDs for simulating payment outcomes:
- Cards that succeed
- Cards that fail with specific error codes (insufficient funds, expired, etc.)
- UPI flows

These test credentials will be used to populate the synthetic evaluation dataset. The specific test values will be documented in the development setup guide once integration begins.

**Reference:** https://razorpay.com/docs/payments/payments/test-card-details/
