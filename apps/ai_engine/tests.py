from django.test import SimpleTestCase

from .services import AIDecisionEngine, AIProviderError, diagnose_and_recommend


class ValidProvider:
    def analyze(self, context):
        return {
            'failure_category': 'NETWORK_ERROR',
            'recommended_action': 'RETRY_PAYMENT',
            'confidence': 'HIGH',
            'suggested_timing': 'IMMEDIATE',
            'reasoning_summary': 'Transient gateway failure is likely.',
        }


class InvalidProvider:
    def analyze(self, context):
        return {'recommended_action': 'CHARGE_CARD_DIRECTLY'}


class FailingProvider:
    def analyze(self, context):
        raise AIProviderError('provider unavailable')


class AIDecisionEngineTests(SimpleTestCase):
    def test_valid_structured_provider_output_is_returned(self):
        response = diagnose_and_recommend({}, provider=ValidProvider())

        self.assertEqual(response['failure_category'], 'NETWORK_ERROR')
        self.assertEqual(response['recommended_action'], 'RETRY_PAYMENT')
        self.assertEqual(response['confidence'], 'HIGH')
        self.assertFalse(response['used_fallback'])

    def test_provider_failure_uses_safe_fallback(self):
        response = diagnose_and_recommend({}, provider=FailingProvider())

        self.assertTrue(response['used_fallback'])
        self.assertEqual(response['recommended_action'], 'ESCALATE_TO_HUMAN')
        self.assertEqual(response['confidence'], 'LOW')

    def test_invalid_provider_output_uses_safe_fallback(self):
        response = AIDecisionEngine(InvalidProvider()).decide({})

        self.assertTrue(response['used_fallback'])
        self.assertEqual(response['failure_category'], 'UNKNOWN')
