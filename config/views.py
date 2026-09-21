from django.shortcuts import render


def public_home(request):
    return render(request, 'public/landing.html', {
        'audiences': [
            ('bi-cloud', 'SaaS businesses', 'Recurring billing teams managing payment continuity.'),
            ('bi-arrow-repeat', 'Subscription businesses', 'Businesses where each billing cycle matters.'),
            ('bi-cart3', 'E-commerce', 'Teams turning payment failure signals into clear next steps.'),
            ('bi-heart-pulse', 'Gyms & fitness', 'Membership operations with recurring collections.'),
            ('bi-mortarboard', 'EdTech', 'Education businesses managing regular fee payments.'),
            ('bi-people', 'Membership businesses', 'Organizations with ongoing member relationships.'),
            ('bi-building', 'B2B recurring revenue', 'Revenue operations teams that need auditability.'),
        ],
        'features': [
            ('bi-radar', 'Failed payment detection', 'Bring payment failure events into a structured recovery case.'),
            ('bi-robot', 'AI diagnosis & recommendation', 'Use payment context and history to recommend a bounded intervention.'),
            ('bi-shield-check', 'Deterministic guardrails', 'Validate every recommendation against merchant policy before execution.'),
            ('bi-lightning-charge', 'Bounded recovery actions', 'Execute only approved retry, payment-link, reminder, escalation, or stop actions.'),
            ('bi-check2-circle', 'Outcome tracking', 'Keep actions separate from confirmed recovery results.'),
            ('bi-bar-chart-line', 'Revenue analytics', 'Measure risk and recovered revenue from persisted records.'),
            ('bi-journal-check', 'Audit trail', 'Connect decisions, interventions, actions, and outcomes.'),
            ('bi-person-workspace', 'Merchant workspace', 'Give revenue teams one scoped place to operate their cases.'),
        ],
    })
