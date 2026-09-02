# Security and Data Protection — AI Revenue Recovery Platform

---

## Overview

The platform handles payment metadata and interacts with external payment gateways. While the MVP does not process real money, it must be designed with production-grade security principles from day one.

**Core Philosophy:**
1. Assume all inputs are hostile
2. Assume the AI engine may hallucinate or generate malicious outputs
3. Keep secrets out of the codebase
4. Enforce strict authorization boundaries
5. Audit everything

---

## API Key Protection

- **No hardcoded secrets:** No API keys, webhook secrets, database passwords, or AI provider keys are committed to the codebase.
- **Environment variables:** All secrets are loaded via environment variables at startup.
- **Secret manager integration:** In production, environment variables would be injected by a secret manager (AWS Secrets Manager, HashiCorp Vault) rather than a `.env` file.
- **Merchant-level keys:** If the platform supports multiple merchants with distinct Razorpay credentials, those keys are stored encrypted in the PostgreSQL database using a strong symmetric encryption algorithm (e.g., AES-256-GCM) with the master key provided via environment variable.

---

## Authorization & Access Control

### Platform Level
- Django's built-in authentication system manages admin and merchant user access.
- Role-based access control (RBAC) ensures users can only access their own merchant data.
- The `AuditLog` table enforces read-only access for all application users.

### AI Engine Level
- The AI engine operates with the lowest possible privilege.
- It does not have database write access.
- It cannot execute network requests to external APIs directly.
- The AI context payload contains only necessary metadata — no raw API keys are ever passed to the LLM prompt.

### Guardrail Level
- The deterministic guardrail layer acts as the authorization gatekeeper for all actions.
- Any action requires explicit approval from the guardrail engine before proceeding to the executor.

---

## Payment Action Guardrails

Security against errant or malicious payment actions is enforced by the deterministic policy engine:

1. **Idempotency:** Every action execution attempt generates a unique idempotency key. This prevents duplicate actions resulting from network retries or system errors.
2. **Rate Limiting:** The guardrail enforces limits on the number of recovery attempts per case (e.g., max 3 attempts) and per time window.
3. **Amount Thresholds:** High-value recovery attempts automatically escalate to human review. The AI cannot bypass this rule.
4. **Stopping Rules:** If a customer explicitly declines a charge or the payment method is permanently invalidated, the guardrail permanently blocks further recovery attempts.

---

## Sensitive Data Handling

- **No Card Data Stored:** The platform does not store full credit card numbers, CVVs, or bank account details. It only stores Razorpay entity IDs (payment IDs, customer IDs).
- **PII Minimization:** Customer Personally Identifiable Information (PII) such as name and email is stored only for operational purposes (e.g., sending payment links). It is not passed to the AI engine unless strictly necessary for generating communication templates (out of scope for MVP).
- **Data Redaction:** The audit log automatically redacts any potentially sensitive fields before writing the event context.

---

## AI Safety

AI systems introduce unique security risks (prompt injection, hallucinations).

- **Structured Prompts:** The AI engine uses structured, deterministic prompts. User input (e.g., customer complaints) is never blindly concatenated into the prompt.
- **Output Validation:** The AI response must pass strict JSON schema validation. If the output contains unrecognised actions or fails schema checks, the system rejects it and applies a safe fallback action.
- **No Direct Execution:** As stated repeatedly, the AI never directly executes actions. Its output is merely a recommendation to the guardrail layer.

---

## Webhook Security

- All incoming Razorpay webhooks are verified using HMAC-SHA256 signatures.
- Webhook endpoints enforce idempotency to handle duplicate deliveries gracefully.
- Requests with missing or invalid signatures are rejected with HTTP 400 and logged as potential security incidents.

---

## Production Considerations (Post-MVP)

For a production deployment, the following additional measures would be required:
- PCI DSS compliance (if handling raw card data, though the current design avoids this)
- SOC 2 Type II compliance
- Network segregation (VPCs, private subnets for database)
- Regular vulnerability scanning and penetration testing
- Multi-factor authentication (MFA) for all merchant and admin accounts
- Data retention and deletion policies (GDPR/CCPA compliance)
