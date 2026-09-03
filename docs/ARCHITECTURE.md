# System Architecture

## Overview
The AI Revenue Recovery Platform is a B2B SaaS system designed to detect, diagnose, and recover failed payments. It is built as a monolithic web application using Django, integrating with a PostgreSQL database and an AI provider for intelligent decision-making, bounded by a strict deterministic guardrail system. 

## High-Level Architecture

The system consists of the following major components:
- **Web Layer**: Django (WSGI/ASGI), handling HTTP requests, admin interfaces, and webhooks.
- **Application Layer (Django Apps)**: Business logic divided into focused modules.
- **Data Layer**: PostgreSQL database for persistent storage and audit logging.
- **External Integrations**:
  - **Razorpay**: For payment gateway integration (Test Mode for MVP).
  - **LLM Provider**: For AI diagnosis and recovery recommendations (provider-agnostic).

## Django App/Module Responsibilities

To maintain separation of concerns, the project is divided into the following Django apps:

1. **`core`**: Base models, common utilities, and system-wide configurations.
2. **`payments`**: Handles synchronization and integration with Razorpay. Manages the ingress of failed payments and webhooks.
3. **`recovery`**: The central orchestrator. Manages the lifecycle of a recovery case (Detect, Diagnose, Decide, Guard, Act, Recover).
4. **`intelligence`**: Encapsulates the AI prompt management, communication with the LLM, and parsing of AI responses.
5. **`guardrails`**: Deterministic rule engine. Validates AI recommendations against business rules (e.g., max retries, blackout windows).
6. **`audit`**: Immutable logging of all state changes, AI decisions, guardrail interventions, and recovery outcomes.

## Razorpay Integration Boundary

The Razorpay integration acts as the sole entry point for payment events and the sole execution point for money-related actions.
- **Ingress**: Razorpay webhooks (e.g., `payment.failed`, `subscription.charged`) are ingested by the `payments` app and translated into internal representations.
- **Egress**: Bounded recovery actions (e.g., retrying a charge, generating a payment link) are converted from internal representations into Razorpay API calls.
- **Boundary Rule**: The AI never communicates directly with Razorpay. The `recovery` app translates approved actions into gateway commands.

## Evaluation Architecture

The evaluation architecture is designed to validate the system's performance and safety without relying on live production traffic:
1. **Synthetic Dataset**: A fixture of 100-500 simulated failed payment records covering various edge cases (insufficient funds, expired card, blocked by issuer).
2. **Simulation Runner**: A script that injects synthetic records into the `payments` ingress pipeline.
3. **Evaluation Metrics**: Compares AI recommendations against expected baseline behaviors, tracks guardrail intervention rates, and measures simulated recovery success.
4. **Safety Assertions**: Automated tests ensure the AI cannot bypass guardrails (e.g., proposing an action that violates retry limits).

## Path to Multi-Tenant SaaS

While the MVP is focused on a single-tenant or limited multi-tenant model, the architecture is designed to evolve into a full multi-tenant SaaS:
1. **Tenant Isolation**: Future iterations will introduce a `Merchant` or `Organization` model. All core data models (Payments, Recovery Cases, Audit Logs) will have a foreign key to the `Tenant`.
2. **Custom Guardrails**: The `guardrails` app will be extended to allow tenant-specific rules (e.g., Tenant A allows 3 retries, Tenant B allows 5).
3. **Data Segregation**: Row-level security (RLS) in PostgreSQL can be implemented to enforce strict data isolation between tenants.
4. **API-First Egress**: The monolithic admin dashboard will evolve into a set of REST APIs for tenant-facing dashboards and webhooks for tenant systems.
