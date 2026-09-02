# Development Roadmap — AI Revenue Recovery Platform

---

## MVP Scope (Razorpay Buildathon Track)

The initial MVP focuses strictly on proving the core recovery loop (Detect → Diagnose → Decide → Guard → Act → Recover → Measure → Audit) using Razorpay Test Mode and a synthetic evaluation dataset.

### Phase 0: Foundation (Current)
- [x] Establish project documentation structure
- [x] Define architecture and data models
- [x] Define AI and guardrail contracts
- [x] Set up empty folder structure and `.gitignore`

### Phase 1: Core Data Model
- [ ] Initialize Django project
- [ ] Implement foundational models (`Merchant`, `Customer`, `Payment`, `Subscription`, `PaymentFailure`)
- [ ] Set up Django Admin with Jazzmin

### Phase 2: Payment Ingestion
- [ ] Integrate Razorpay Test Mode API
- [ ] Implement payment and subscription ingestion scripts/views
- [ ] Implement Razorpay webhook receiver for failure events

### Phase 3: Revenue-Risk Detection
- [ ] Implement detection logic to identify actionable failures
- [ ] Implement `RecoveryCase` creation

### Phase 4: AI Diagnosis
- [ ] Implement `AIEngineInterface` and specific provider adapter
- [ ] Implement context payload construction
- [ ] Implement prompt construction and JSON parsing
- [ ] Handle AI failure modes

### Phase 5: Recovery Decision Engine
- [ ] Connect AI output to `RecoveryDecision` proposition

### Phase 6: Guardrails
- [ ] Implement deterministic policy engine evaluation rules
- [ ] Implement merchant policy configuration
- [ ] Connect decision proposition to guardrail evaluation

### Phase 7: Action Execution
- [ ] Implement action executors (Retry, Payment Link, Escalation, etc.)
- [ ] Enforce idempotency

### Phase 8: Recovery Measurement
- [ ] Implement webhook handling for successful recovery events
- [ ] Implement basic analytics dashboard views

### Phase 9: Audit System
- [ ] Implement immutable `AuditLog`
- [ ] Wire audit logging into all workflow transitions

### Phase 10: Evaluation
- [ ] Generate synthetic evaluation dataset (fixtures)
- [ ] Implement evaluation reporting scripts

### Phase 11: UI/UX Polish
- [ ] Refine Django Admin interface
- [ ] Build basic frontend views for merchant dashboard

### Phase 12: Final Buildathon Submission
- [ ] Finalize documentation
- [ ] Record demonstration video

---

## Future Commercial Product (Post-MVP)

These features represent the strategic direction of the product but are explicitly excluded from the current MVP build to maintain focus.

- **Multi-Gateway Support:** Integrate Stripe, PayPal, and others
- **Multi-Channel Communication:** SMS and WhatsApp recovery notifications
- **Custom Guardrail Builder:** Allow merchants to build visual recovery policies
- **Predictive Churn Signals:** Detect customers likely to fail *before* the billing cycle
- **Public API:** Allow merchants to trigger recovery workflows via API
- **SaaS Billing:** Implement subscription billing for the platform itself
