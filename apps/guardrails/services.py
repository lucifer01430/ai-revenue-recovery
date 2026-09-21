from datetime import timedelta

from django.utils import timezone

from apps.recovery.models import (
    AuthorizationChoices,
    ExecutionChoices,
    RecoveryActionChoices,
    RecoveryPolicy,
    ResultChoices,
)


def _decision(status, action, reason_code, reason):
    return {
        'approved': status == AuthorizationChoices.APPROVED,
        'authorization_status': status,
        'modified_recommendation': action,
        'reason_code': reason_code,
        'reason': reason,
    }


def validate_action(recovery_case, recommendation):
    """Apply deterministic policy rules and fail closed on evaluation errors."""
    try:
        policy, _ = RecoveryPolicy.objects.get_or_create(merchant=recovery_case.payment.merchant)
        now = timezone.now()
        retry_actions = {
            RecoveryActionChoices.RETRY_PAYMENT,
            RecoveryActionChoices.SCHEDULE_RETRY,
        }

        # Rule 1: retry limit, based on executed retry actions and the case counter.
        executed_retries = recovery_case.recovery_actions.filter(
            action_type__in=retry_actions,
            execution_status=ExecutionChoices.EXECUTED,
        ).count()
        retry_count = max(recovery_case.retries_attempted, executed_retries)
        if recommendation in retry_actions and retry_count >= policy.max_retries_per_case:
            return _decision(
                AuthorizationChoices.ESCALATED,
                RecoveryActionChoices.ESCALATE_TO_HUMAN,
                'RETRY_LIMIT_EXCEEDED',
                f'Max retries ({policy.max_retries_per_case}) exceeded.',
            )

        # Rule 2: recovery window.
        window_started = recovery_case.payment.created_at or recovery_case.created_at
        if now > window_started + timedelta(days=policy.recovery_window_days):
            return _decision(
                AuthorizationChoices.REJECTED,
                RecoveryActionChoices.STOP_RECOVERY,
                'RECOVERY_WINDOW_EXPIRED',
                'The recovery window has expired.',
            )

        # Rule 3: duplicate action prevention.
        cooldown_started = now - timedelta(hours=policy.duplicate_action_cooldown_hours)
        duplicate_exists = recovery_case.recovery_actions.filter(
            action_type=recommendation,
            execution_status=ExecutionChoices.EXECUTED,
            executed_at__gte=cooldown_started,
        ).exists()
        if duplicate_exists:
            return _decision(
                AuthorizationChoices.REJECTED,
                RecoveryActionChoices.STOP_RECOVERY,
                'DUPLICATE_ACTION_PREVENTED',
                'The same action was already executed within the cooldown window.',
            )

        # Rule 4: high-value escalation.
        if recovery_case.payment.amount_paise > policy.high_value_threshold_paise:
            return _decision(
                AuthorizationChoices.ESCALATED,
                RecoveryActionChoices.ESCALATE_TO_HUMAN,
                'HIGH_VALUE_REQUIRES_APPROVAL',
                'High-value recovery requires human approval.',
            )

        # Rule 5: repeated failed recovery escalation.
        failed_attempts = recovery_case.recovery_results.filter(status=ResultChoices.FAILED).count()
        if failed_attempts >= policy.escalation_failure_threshold:
            return _decision(
                AuthorizationChoices.ESCALATED,
                RecoveryActionChoices.ESCALATE_TO_HUMAN,
                'REPEATED_FAILURE_ESCALATION',
                'Repeated failed recovery attempts require human review.',
            )

        # Rule 6: stopping conditions.
        diagnosis = str(recovery_case.latest_diagnosis or '').lower()
        description = str(recovery_case.payment.description or '').lower()
        permanently_invalid = any(term in f'{diagnosis} {description}' for term in ('permanently invalid', 'permanently blocked'))
        fraud_retry = policy.no_retry_on_fraud and 'fraud' in diagnosis and recommendation in retry_actions
        pending_too_long = recovery_case.recovery_results.filter(
            status=ResultChoices.PENDING_RESULT,
            created_at__lt=now - timedelta(days=policy.abandonment_timeout_days),
        ).exists()
        if recommendation == RecoveryActionChoices.STOP_RECOVERY or permanently_invalid or fraud_retry or pending_too_long:
            return _decision(
                AuthorizationChoices.REJECTED,
                RecoveryActionChoices.STOP_RECOVERY,
                'STOPPING_RULE_TRIGGERED',
                'A stopping rule prevents further recovery.',
            )

        return _decision(
            AuthorizationChoices.APPROVED,
            recommendation,
            'POLICY_APPROVED',
            'Passed all applicable guardrail rules.',
        )
    except Exception as exc:
        return _decision(
            AuthorizationChoices.REJECTED,
            RecoveryActionChoices.STOP_RECOVERY,
            'GUARDRAIL_EVALUATION_FAILED',
            f'Guardrail evaluation failed safely: {exc}',
        )
