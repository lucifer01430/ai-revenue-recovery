from typing import Any, Mapping, Protocol

from apps.recovery.models import (
    ConfidenceChoices,
    FailureCategoryChoices,
    RecoveryActionChoices,
    TimingChoices,
)


class AIProvider(Protocol):
    """Provider contract for bounded, recommendation-only AI decisions."""

    def analyze(self, context: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


class AIProviderError(Exception):
    """Raised when a provider cannot produce a decision."""


class AIOutputValidationError(AIProviderError):
    """Raised when a provider response violates the documented schema."""


class LocalMockProvider:
    """Deterministic local provider used without an external API key."""

    def analyze(self, context: Mapping[str, Any]) -> Mapping[str, Any]:
        if context.get('_simulate_provider_failure'):
            raise AIProviderError('Simulated provider failure')

        payment = context.get('payment', context)
        error_code = payment.get('failure_reason', payment.get('error_code', ''))
        error_description = payment.get('failure_description', payment.get('error_description', '')).lower()

        if 'insufficient' in error_description or error_code == 'BAD_REQUEST_ERROR':
            return {
                'failure_category': FailureCategoryChoices.INSUFFICIENT_FUNDS,
                'recommended_action': RecoveryActionChoices.RETRY_PAYMENT,
                'confidence': ConfidenceChoices.HIGH,
                'suggested_timing': TimingChoices.AFTER_24H,
                'reasoning_summary': 'Insufficient funds are the most likely cause; retry after a short delay.',
            }
        if 'expired' in error_description:
            return {
                'failure_category': FailureCategoryChoices.CARD_EXPIRED,
                'recommended_action': RecoveryActionChoices.SEND_PAYMENT_LINK,
                'confidence': ConfidenceChoices.HIGH,
                'suggested_timing': TimingChoices.IMMEDIATE,
                'reasoning_summary': 'The card appears expired; ask the customer to use an updated payment method.',
            }
        if 'fraud' in error_description or 'blocked' in error_description:
            return {
                'failure_category': FailureCategoryChoices.CUSTOMER_INITIATED_FAILURE,
                'recommended_action': RecoveryActionChoices.STOP_RECOVERY,
                'confidence': ConfidenceChoices.HIGH,
                'suggested_timing': TimingChoices.NOT_APPLICABLE,
                'reasoning_summary': 'The payment method appears permanently invalid or high risk; stop recovery.',
            }
        return {
            'failure_category': FailureCategoryChoices.UNKNOWN,
            'recommended_action': RecoveryActionChoices.ESCALATE_TO_HUMAN,
            'confidence': ConfidenceChoices.MEDIUM,
            'suggested_timing': TimingChoices.IMMEDIATE,
            'reasoning_summary': 'The available failure signals are ambiguous; route the case for human review.',
        }


class AIDecisionEngine:
    """Validates provider output and applies the documented safe fallback."""

    REQUIRED_FIELDS = {
        'failure_category',
        'recommended_action',
        'confidence',
        'suggested_timing',
        'reasoning_summary',
    }

    def __init__(self, provider: AIProvider | None = None):
        self.provider = provider or LocalMockProvider()

    def decide(self, context: Mapping[str, Any]) -> dict[str, Any]:
        try:
            response = self.validate_output(self.provider.analyze(context))
            response['used_fallback'] = False
            return response
        except Exception as exc:
            return self.fallback_response(str(exc))

    @classmethod
    def validate_output(cls, output: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(output, Mapping):
            raise AIOutputValidationError('Provider response must be an object')

        missing = cls.REQUIRED_FIELDS - set(output.keys())
        if missing:
            raise AIOutputValidationError(f'Missing required fields: {sorted(missing)}')
        if output['failure_category'] not in FailureCategoryChoices.values:
            raise AIOutputValidationError('Invalid failure_category')
        if output['recommended_action'] not in RecoveryActionChoices.values:
            raise AIOutputValidationError('Invalid recommended_action')
        if output['confidence'] not in ConfidenceChoices.values:
            raise AIOutputValidationError('Invalid confidence')
        if output['suggested_timing'] not in TimingChoices.values:
            raise AIOutputValidationError('Invalid suggested_timing')
        if not isinstance(output['reasoning_summary'], str):
            raise AIOutputValidationError('reasoning_summary must be a string')
        if len(output['reasoning_summary']) > 200:
            raise AIOutputValidationError('reasoning_summary exceeds 200 characters')

        return {
            'failure_category': output['failure_category'],
            'recommended_action': output['recommended_action'],
            'confidence': output['confidence'],
            'suggested_timing': output['suggested_timing'],
            'reasoning_summary': output['reasoning_summary'],
        }

    @staticmethod
    def fallback_response(reason: str) -> dict[str, Any]:
        return {
            'failure_category': FailureCategoryChoices.UNKNOWN,
            'recommended_action': RecoveryActionChoices.ESCALATE_TO_HUMAN,
            'confidence': ConfidenceChoices.LOW,
            'suggested_timing': TimingChoices.IMMEDIATE,
            'reasoning_summary': 'AI decision unavailable; escalated for human review.',
            'used_fallback': True,
            'failure_reason': reason,
        }


def diagnose_and_recommend(payment_data, provider: AIProvider | None = None):
    """Compatibility entry point for the bounded AI decision engine."""
    return AIDecisionEngine(provider).decide(payment_data)
