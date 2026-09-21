import base64
import json
import urllib.error
import urllib.request
import uuid

from django.conf import settings

from apps.recovery.models import AuthorizationChoices, RecoveryActionChoices


class RazorpayError(Exception):
    """A safe, provider-neutral error from the Razorpay boundary."""


class RazorpayAdapter:
    """Razorpay Test Mode adapter for bounded recovery operations."""

    def __init__(self, merchant, http_post=None):
        self.merchant = merchant
        self.key_id = merchant.razorpay_key_id
        self.key_secret = merchant.razorpay_key_secret
        self.base_url = getattr(settings, 'RAZORPAY_API_BASE_URL', 'https://api.razorpay.com/v1')
        self.http_post = http_post or self._http_post

    @property
    def configured(self):
        return bool(
            self.key_id.startswith('rzp_test_')
            and self.key_secret
            and self.key_secret not in {'placeholder_secret', 'your_razorpay_test_secret'}
        )

    def create_payment_link(self, action):
        self._assert_allowed(action)
        payload = {
            'amount': action.recovery_case.payment.amount_paise,
            'currency': action.recovery_case.payment.currency,
            'description': 'Payment recovery link',
            'customer': {
                'name': action.recovery_case.payment.customer.name,
                'email': action.recovery_case.payment.customer.email,
            },
            'notify': {'sms': False, 'email': True},
            'reference_id': str(action.id),
        }
        if not self.configured:
            return {'id': f'plink_sim_{action.id.hex[:12]}', 'status': 'created', 'simulated': True}
        return self.http_post('/payment_links', payload, self._idempotency_key(action))

    def charge_subscription(self, action, subscription_id, currency='INR'):
        self._assert_allowed(action)
        if not self.configured:
            return {'id': f'pay_sim_{action.id.hex[:12]}', 'status': 'created', 'simulated': True}
        payload = {
            'amount': action.recovery_case.payment.amount_paise,
            'currency': currency,
            'description': 'Subscription recovery charge',
        }
        return self.http_post(f'/subscriptions/{subscription_id}/charge', payload, self._idempotency_key(action))

    def _assert_allowed(self, action):
        if action.authorization_status != AuthorizationChoices.APPROVED:
            raise RazorpayError('Recovery action was not approved by guardrails')

    @staticmethod
    def _idempotency_key(action):
        return f'recovery-{action.id}-{action.action_type}'

    def _http_post(self, path, payload, idempotency_key):
        credentials = base64.b64encode(f'{self.key_id}:{self.key_secret}'.encode()).decode()
        request = urllib.request.Request(
            f'{self.base_url.rstrip("/")}{path}',
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/json',
                'X-Razorpay-Idempotency': idempotency_key,
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                if response.status >= 400:
                    raise RazorpayError('Razorpay returned an error')
                return json.loads(response.read().decode('utf-8'))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise RazorpayError('Razorpay request failed') from exc


def execute_gateway_action(action):
    """Execute only the gateway portion of an already-approved action."""
    adapter = RazorpayAdapter(action.recovery_case.payment.merchant)
    if action.action_type in {RecoveryActionChoices.SEND_PAYMENT_LINK, RecoveryActionChoices.RETRY_PAYMENT}:
        return adapter.create_payment_link(action)
    return {'status': 'accepted', 'simulated': True}
