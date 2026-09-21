from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.customers.models import Customer
from apps.merchants.models import Merchant
from apps.payments.models import Payment
from apps.recovery.models import (
    AuthorizationChoices,
    ExecutionChoices,
    RecoveryAction,
    RecoveryActionChoices,
    RecoveryCase,
    RecoveryPolicy,
    RecoveryResult,
    ResultChoices,
)
from .services import validate_action


class GuardrailEngineTests(TestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(
            name='Guardrail Merchant',
            email='guardrails@example.com',
            razorpay_key_id='rzp_test_guardrails',
            razorpay_key_secret='secret',
        )
        customer = Customer.objects.create(
            merchant=self.merchant,
            razorpay_customer_id='cust_guardrails',
            name='Guardrail Customer',
            email='customer@example.com',
        )
        payment = Payment.objects.create(
            merchant=self.merchant,
            customer=customer,
            razorpay_payment_id='pay_guardrails',
            amount_paise=25000,
            status='failed',
            description='Payment failed',
        )
        self.case = RecoveryCase.objects.create(payment=payment)
        self.policy = RecoveryPolicy.objects.create(merchant=self.merchant)

    def test_approved_action(self):
        result = validate_action(self.case, RecoveryActionChoices.RETRY_PAYMENT)
        self.assertEqual(result['authorization_status'], AuthorizationChoices.APPROVED)

    def test_retry_limit_escalates(self):
        self.case.retries_attempted = 3
        self.case.save(update_fields=['retries_attempted'])
        result = validate_action(self.case, RecoveryActionChoices.RETRY_PAYMENT)
        self.assertEqual(result['reason_code'], 'RETRY_LIMIT_EXCEEDED')
        self.assertEqual(result['authorization_status'], AuthorizationChoices.ESCALATED)

    def test_recovery_window_rejects(self):
        RecoveryCase.objects.filter(pk=self.case.pk).update(
            created_at=timezone.now() - timedelta(days=8),
        )
        Payment.objects.filter(pk=self.case.payment_id).update(
            created_at=timezone.now() - timedelta(days=8),
        )
        self.case.refresh_from_db()
        result = validate_action(self.case, RecoveryActionChoices.SEND_REMINDER)
        self.assertEqual(result['reason_code'], 'RECOVERY_WINDOW_EXPIRED')
        self.assertEqual(result['authorization_status'], AuthorizationChoices.REJECTED)

    def test_duplicate_action_rejects(self):
        action = RecoveryAction.objects.create(
            recovery_case=self.case,
            action_type=RecoveryActionChoices.SEND_REMINDER,
            authorization_status=AuthorizationChoices.APPROVED,
            execution_status=ExecutionChoices.EXECUTED,
            executed_at=timezone.now(),
        )
        RecoveryResult.objects.create(
            recovery_case=self.case,
            recovery_action=action,
            status=ResultChoices.PENDING_RESULT,
        )
        result = validate_action(self.case, RecoveryActionChoices.SEND_REMINDER)
        self.assertEqual(result['reason_code'], 'DUPLICATE_ACTION_PREVENTED')
        self.assertEqual(result['authorization_status'], AuthorizationChoices.REJECTED)

    def test_high_value_payment_escalates(self):
        self.case.payment.amount_paise = 60000
        self.case.payment.save(update_fields=['amount_paise'])
        result = validate_action(self.case, RecoveryActionChoices.SEND_PAYMENT_LINK)
        self.assertEqual(result['reason_code'], 'HIGH_VALUE_REQUIRES_APPROVAL')
        self.assertEqual(result['authorization_status'], AuthorizationChoices.ESCALATED)

    def test_fraud_stopping_rule_rejects(self):
        self.case.latest_diagnosis = 'High risk of fraud.'
        self.case.save(update_fields=['latest_diagnosis'])
        result = validate_action(self.case, RecoveryActionChoices.RETRY_PAYMENT)
        self.assertEqual(result['reason_code'], 'STOPPING_RULE_TRIGGERED')
        self.assertEqual(result['modified_recommendation'], RecoveryActionChoices.STOP_RECOVERY)

    def test_failed_attempt_threshold_escalates(self):
        for index in range(2):
            action = RecoveryAction.objects.create(
                recovery_case=self.case,
                action_type=RecoveryActionChoices.SEND_REMINDER,
                authorization_status=AuthorizationChoices.APPROVED,
                execution_status=ExecutionChoices.EXECUTED,
                executed_at=timezone.now() - timedelta(days=index + 1),
            )
            RecoveryResult.objects.create(
                recovery_case=self.case,
                recovery_action=action,
                status=ResultChoices.FAILED,
            )
        result = validate_action(self.case, RecoveryActionChoices.SEND_PAYMENT_LINK)
        self.assertEqual(result['reason_code'], 'REPEATED_FAILURE_ESCALATION')
        self.assertEqual(result['authorization_status'], AuthorizationChoices.ESCALATED)

    def test_guardrail_failure_fails_safe(self):
        with patch.object(RecoveryPolicy.objects, 'get_or_create', side_effect=RuntimeError('database unavailable')):
            result = validate_action(self.case, RecoveryActionChoices.RETRY_PAYMENT)
        self.assertEqual(result['reason_code'], 'GUARDRAIL_EVALUATION_FAILED')
        self.assertEqual(result['authorization_status'], AuthorizationChoices.REJECTED)
        self.assertFalse(result['approved'])
