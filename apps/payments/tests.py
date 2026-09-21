import hashlib
import hmac
import json

from django.conf import settings
from django.test import Client, TestCase

from apps.payments.models import Payment, PaymentEvent
from apps.recovery.models import RecoveryAction, RecoveryCase, RecoveryResult
from apps.recovery.services import process_failed_payment, record_recovery_outcome
from apps.merchants.models import Merchant
from apps.customers.models import Customer
from apps.payments.services import RazorpayAdapter
from apps.recovery.models import AuthorizationChoices


class PaymentWebhookTestCase(TestCase):
    url = '/webhooks/razorpay/'

    def signed_post(self, payload, event_id='evt_test_1', signature_secret=None):
        body = json.dumps(payload).encode()
        secret = signature_secret or settings.RAZORPAY_WEBHOOK_SECRET
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return self.client.post(
            self.url,
            data=body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=signature,
            HTTP_X_RAZORPAY_EVENT_ID=event_id,
        )

    def test_missing_and_invalid_signatures_are_rejected(self):
        payload = {'event': 'payment.failed', 'payload': {'payment': {'entity': {'id': 'pay_sig'}}}}
        missing = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(missing.status_code, 400)
        invalid = self.client.post(
            self.url, data=json.dumps(payload), content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='invalid', HTTP_X_RAZORPAY_EVENT_ID='evt_invalid',
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(PaymentEvent.objects.count(), 0)

    def test_valid_failure_event_is_persisted_and_duplicate_is_idempotent(self):
        payload = {
            'event': 'payment.failed',
            'payload': {'payment': {'entity': {
                'id': 'pay_webhook_failure', 'amount': 25000, 'currency': 'INR',
                'error_code': 'CARD_ERROR', 'error_description': 'Card expired',
            }}},
        }
        first = self.signed_post(payload, 'evt_failure_1')
        duplicate = self.signed_post(payload, 'evt_failure_1')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(PaymentEvent.objects.count(), 1)
        self.assertEqual(RecoveryCase.objects.count(), 1)
        self.assertEqual(RecoveryAction.objects.count(), 1)
        self.assertEqual(PaymentEvent.objects.get().status, PaymentEvent.PROCESSED)

    def test_success_event_records_outcome_and_duplicate_does_not_change_it(self):
        process_failed_payment({
            'id': 'pay_success_event', 'amount': 25000, 'currency': 'INR',
            'error_code': 'CARD_ERROR', 'error_description': 'Card expired',
        })
        action = RecoveryAction.objects.get(recovery_case__payment__razorpay_payment_id='pay_success_event')
        payload = {
            'event': 'payment.captured',
            'payload': {'payment': {'entity': {'id': 'pay_success_event', 'amount': 25000}}},
        }
        self.assertEqual(self.signed_post(payload, 'evt_success_1').status_code, 200)
        self.assertEqual(self.signed_post(payload, 'evt_success_1').status_code, 200)
        result = RecoveryResult.objects.get(recovery_action=action)
        self.assertEqual(result.status, 'RECOVERED')
        self.assertEqual(Payment.objects.get(razorpay_payment_id='pay_success_event').status, 'captured')
        self.assertEqual(RecoveryResult.objects.filter(recovery_action=action).count(), 1)

    def test_failed_outcome_is_recorded_once(self):
        process_failed_payment({
            'id': 'pay_failed_outcome', 'amount': 25000, 'currency': 'INR',
            'error_code': 'CARD_ERROR', 'error_description': 'Card expired',
        })
        action = RecoveryAction.objects.get(recovery_case__payment__razorpay_payment_id='pay_failed_outcome')
        result, changed = record_recovery_outcome(action, 'FAILED', source='SIMULATION')
        duplicate, changed_again = record_recovery_outcome(action, 'FAILED', source='SIMULATION')
        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(result.id, duplicate.id)
        self.assertEqual(RecoveryCase.objects.get(id=action.recovery_case_id).status, 'FAILED')

    def test_razorpay_test_mode_adapter_uses_mocked_api_response(self):
        merchant = Merchant.objects.create(
            name='Test Mode Merchant', email='test@example.com',
            razorpay_key_id='rzp_test_123', razorpay_key_secret='secret',
        )
        customer = Customer.objects.create(
            merchant=merchant, razorpay_customer_id='cust_adapter',
            name='Adapter Customer', email='customer@example.com',
        )
        payment = Payment.objects.create(
            merchant=merchant, customer=customer, razorpay_payment_id='pay_adapter',
            amount_paise=5000, currency='INR', status='failed',
        )
        case = RecoveryCase.objects.create(payment=payment, status='ACTION_PENDING')
        action = RecoveryAction.objects.create(
            recovery_case=case, action_type='SEND_PAYMENT_LINK',
            authorization_status=AuthorizationChoices.APPROVED,
        )
        calls = []

        def fake_post(path, payload, idempotency_key):
            calls.append((path, payload, idempotency_key))
            return {'id': 'plink_test_123', 'status': 'created'}

        response = RazorpayAdapter(merchant, http_post=fake_post).create_payment_link(action)
        self.assertEqual(response['id'], 'plink_test_123')
        self.assertEqual(calls[0][0], '/payment_links')
        self.assertEqual(calls[0][1]['reference_id'], str(action.id))
        self.assertIn(str(action.id), calls[0][2])
