from django.test import TestCase
from django.contrib.auth import get_user_model
from django.conf import settings
from apps.recovery.services import execute_action, process_failed_payment
from apps.recovery.models import RecoveryCase
from apps.recovery.models import (
    AIDiagnosis,
    AIRecommendation,
    GuardrailIntervention,
    RecoveryAction,
    RecoveryPolicy,
    RecoveryResult,
)
from apps.audit.models import AuditLog
from apps.merchants.models import Merchant


class FailingProvider:
    def analyze(self, context):
        raise RuntimeError('provider unavailable')


class RecoveryFlowTestCase(TestCase):
    def test_dashboard_uses_persisted_outcomes(self):
        user = get_user_model().objects.create_user(username='dashboard_owner', password='safe-pass-123')
        Merchant.objects.create(
            owner=user, name='Demo Merchant', email='owner@example.com',
            razorpay_key_id=settings.RAZORPAY_KEY_ID,
            razorpay_key_secret=settings.RAZORPAY_KEY_SECRET,
        )
        process_failed_payment({
            'id': 'pay_dashboard_metrics',
            'amount': 25000,
            'currency': 'INR',
            'error_code': 'BAD_REQUEST_ERROR',
            'error_description': 'Payment failed due to insufficient funds',
        })
        self.client.force_login(user)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['revenue_at_risk'], 250.0)
        self.assertEqual(response.context['revenue_recovered'], 250.0)
        self.assertEqual(response.context['successful_recoveries'], 1)
        self.assertEqual(response.context['open_cases'], 0)

    def test_end_to_end_recovery_flow(self):
        # 1. Simulate webhook payload for failed payment
        mock_payment_entity = {
            'id': 'pay_failed_12345',
            'amount': 25000, # 250 INR, below the default high-value threshold
            'currency': 'INR',
            'error_code': 'BAD_REQUEST_ERROR',
            'error_description': 'Payment failed due to insufficient funds'
        }
        
        # 2. Process it
        process_failed_payment(mock_payment_entity)
        
        # 3. Assertions
        case = RecoveryCase.objects.get(payment__razorpay_payment_id='pay_failed_12345')
        
        # Check case status (after mock successful retry)
        self.assertEqual(case.status, 'RECOVERED')
        
        # Check AI diagnosis was stored
        self.assertIn('insufficient', case.latest_diagnosis.lower())
        self.assertEqual(case.latest_recommendation, 'RETRY_PAYMENT')

        diagnosis = AIDiagnosis.objects.get(recovery_case=case)
        self.assertEqual(diagnosis.failure_category, 'INSUFFICIENT_FUNDS')
        self.assertEqual(diagnosis.confidence, 'HIGH')
        recommendation = AIRecommendation.objects.get(diagnosis=diagnosis)
        self.assertEqual(recommendation.recommended_action, 'RETRY_PAYMENT')

        action = RecoveryAction.objects.get(recovery_case=case)
        self.assertEqual(action.authorization_status, 'APPROVED')
        self.assertEqual(action.execution_status, 'EXECUTED')
        result = RecoveryResult.objects.get(recovery_action=action)
        self.assertEqual(result.status, 'RECOVERED')
        self.assertEqual(result.recovered_amount_paise, 25000)
        self.assertEqual(RecoveryPolicy.objects.get(merchant=case.payment.merchant).max_retries_per_case, 3)
        
        # Check Audit Logs
        logs = AuditLog.objects.filter(recovery_case_id=case.id).order_by('created_at')
        self.assertEqual(logs.count(), 5)
        
        event_types = [log.event_type for log in logs]
        self.assertEqual(event_types, [
            'CASE_CREATED',
            'AI_DIAGNOSED',
            'GUARDRAIL_EVALUATED',
            'PAYMENT_OUTCOME_APPLIED',
            'ACTION_EXECUTED'
        ])
        
        print("\n\n--- SUCCESS: E2E Recovery Flow Tested Successfully ---")
        for log in logs:
            print(f"[{log.event_type}] {log.description}")
        print("------------------------------------------------------\n")

    def test_action_execution_waits_for_recorded_outcome(self):
        process_failed_payment({
            'id': 'pay_expired_12345',
            'amount': 25000,
            'currency': 'INR',
            'error_code': 'CARD_ERROR',
            'error_description': 'Card expired',
        })

        case = RecoveryCase.objects.get(payment__razorpay_payment_id='pay_expired_12345')
        action = RecoveryAction.objects.get(recovery_case=case)
        result = RecoveryResult.objects.get(recovery_action=action)
        self.assertEqual(action.execution_status, 'EXECUTED')
        self.assertEqual(result.status, 'PENDING_RESULT')
        self.assertEqual(case.status, 'ACTION_PENDING')

    def test_retry_limit_creates_intervention_and_does_not_execute(self):
        process_failed_payment({
            'id': 'pay_retry_limit_12345',
            'amount': 100000,
            'currency': 'INR',
            'error_code': 'BAD_REQUEST_ERROR',
            'error_description': 'Payment failed due to insufficient funds',
        })
        case = RecoveryCase.objects.get(payment__razorpay_payment_id='pay_retry_limit_12345')
        case.retries_attempted = 3
        case.save(update_fields=['retries_attempted'])

        process_failed_payment({
            'id': 'pay_retry_limit_12345',
            'amount': 100000,
            'currency': 'INR',
            'error_code': 'BAD_REQUEST_ERROR',
            'error_description': 'Payment failed due to insufficient funds',
        })

        intervention = GuardrailIntervention.objects.filter(recovery_case=case).order_by('-created_at').first()
        action = RecoveryAction.objects.filter(recovery_case=case).order_by('-created_at').first()
        result = RecoveryResult.objects.get(recovery_action=action)
        self.assertEqual(intervention.reason_code, 'RETRY_LIMIT_EXCEEDED')
        self.assertEqual(intervention.decision, 'ESCALATED')
        self.assertEqual(action.execution_status, 'BLOCKED')
        self.assertEqual(result.status, 'ESCALATED')
        result_count = RecoveryResult.objects.filter(recovery_case=case).count()
        self.assertFalse(execute_action(case, action))
        self.assertEqual(RecoveryResult.objects.filter(recovery_case=case).count(), result_count)

    def test_provider_failure_persists_fallback_and_audit(self):
        process_failed_payment({
            'id': 'pay_ai_failure_12345',
            'amount': 25000,
            'currency': 'INR',
            'error_code': 'UNKNOWN',
            'error_description': 'Unclear payment failure',
        }, provider=FailingProvider())

        case = RecoveryCase.objects.get(payment__razorpay_payment_id='pay_ai_failure_12345')
        diagnosis = AIDiagnosis.objects.get(recovery_case=case)
        recommendation = AIRecommendation.objects.get(diagnosis=diagnosis)
        self.assertEqual(diagnosis.confidence, 'LOW')
        self.assertEqual(recommendation.recommended_action, 'ESCALATE_TO_HUMAN')
        self.assertTrue(AuditLog.objects.filter(recovery_case_id=case.id, event_type='AI_FAILURE').exists())
