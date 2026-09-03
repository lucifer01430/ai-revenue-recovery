# Data Model Architecture

The data model is structured around the core entities of the recovery flow: Payments, Recovery Cases, Intelligence, and Auditing.

## Core Entities (Conceptual)

### 1. Payment & Ingress Models
- **`Customer`**: Represents the end-user who initiated the payment.
- **`Subscription`**: Represents a recurring billing agreement.
- **`PaymentTransaction`**: Represents a specific attempt to move money (success or failure). Maps directly to Razorpay payment objects.
- **`PaymentEvent`**: Raw webhook payloads and parsed events from the payment gateway.

### 2. Recovery Workflow Models
- **`RecoveryCase`**: The central entity. Created when a `PaymentTransaction` fails. Tracks the overall status (Open, Diagnosing, Action Pending, Recovered, Failed, Closed).
- **`RecoveryAction`**: A specific action recommended by the AI or triggered by a policy (e.g., `RETRY_CHARGE`, `SEND_PAYMENT_LINK`, `ESCALATE`).

### 3. Intelligence Models
- **`AIDiagnosis`**: The result of the AI analyzing a `RecoveryCase`. Contains the root cause analysis and confidence score.
- **`AIRecommendation`**: The specific action proposed by the AI based on the diagnosis.

### 4. Guardrail Models
- **`RecoveryPolicy`**: Deterministic rules defined by the business (e.g., `MAX_RETRIES_PER_CASE = 3`, `NO_RETRY_ON_FRAUD = True`).
- **`GuardrailIntervention`**: A record created when the guardrail system blocks or modifies an `AIRecommendation`.

### 5. Audit & Measurement Models
- **`AuditLog`**: An append-only, immutable ledger recording every significant event in a `RecoveryCase` (Case Created, AI Diagnosed, Guardrail Passed/Blocked, Action Executed).
- **`RecoveryMetric`**: Aggregated views/materialized data for dashboard reporting (e.g., Recovered Revenue, AI Accuracy, Guardrail Block Rate).

## Entity Relationships

- A `PaymentTransaction` belongs to a `Customer` (and optionally a `Subscription`).
- A `RecoveryCase` is 1:1 with a failed `PaymentTransaction`.
- A `RecoveryCase` has a 1:1 or 1:N relationship with `AIDiagnosis` and `AIRecommendation` (if multiple attempts are made).
- An `AIRecommendation` must be validated against a `RecoveryPolicy`.
- Every state change in `RecoveryCase` generates an `AuditLog` entry.

*Note: Actual Django models will be implemented in subsequent phases. This document serves as the conceptual blueprint.*
