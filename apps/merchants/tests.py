from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.customers.models import Customer
from apps.payments.models import Payment
from apps.recovery.models import RecoveryCase

from .models import Merchant


class MerchantAuthAndIsolationTests(TestCase):
    def make_user(self, username):
        return get_user_model().objects.create_user(username=username, password='safe-pass-123')

    def make_merchant(self, user, name):
        return Merchant.objects.create(
            owner=user, name=name, email=f'{user.username}@example.com',
            razorpay_key_id=settings.RAZORPAY_KEY_ID,
            razorpay_key_secret=settings.RAZORPAY_KEY_SECRET,
        )

    def make_case(self, merchant, suffix):
        customer = Customer.objects.create(
            merchant=merchant, razorpay_customer_id=f'cust_{suffix}',
            name=f'Customer {suffix}', email=f'{suffix}@example.com',
        )
        payment = Payment.objects.create(
            merchant=merchant, customer=customer, razorpay_payment_id=f'pay_{suffix}',
            amount_paise=10000, currency='INR', status='failed', description='Failed payment',
        )
        return RecoveryCase.objects.create(payment=payment, status='OPEN')

    def test_login_success_and_failure(self):
        self.make_user('login_user')
        self.assertFalse(self.client.login(username='login_user', password='wrong'))
        self.assertTrue(self.client.login(username='login_user', password='safe-pass-123'))

    def test_protected_routes_redirect_unauthenticated_users(self):
        for url in ('/', '/cases/', '/cases/00000000-0000-0000-0000-000000000001/'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login/', response.url)

    def test_onboarding_creates_user_owned_merchant(self):
        user = self.make_user('new_merchant')
        self.client.force_login(user)
        response = self.client.post(reverse('merchant_setup'), {
            'name': 'Acme Learning', 'email': 'ops@acme.example',
        })
        self.assertRedirects(response, reverse('recovery:dashboard'))
        merchant = Merchant.objects.get(owner=user)
        self.assertEqual(merchant.name, 'Acme Learning')
        self.assertEqual(merchant.email, 'ops@acme.example')

    def test_existing_merchant_user_goes_to_dashboard(self):
        user = self.make_user('existing_merchant')
        merchant = self.make_merchant(user, 'Existing Business')
        self.client.force_login(user)
        response = self.client.get(reverse('recovery:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['merchant'], merchant)

    def test_merchant_a_cannot_access_merchant_b_data(self):
        user_a = self.make_user('merchant_a')
        user_b = self.make_user('merchant_b')
        merchant_a = self.make_merchant(user_a, 'Merchant A')
        merchant_b = self.make_merchant(user_b, 'Merchant B')
        self.make_case(merchant_a, 'a')
        case_b = self.make_case(merchant_b, 'b')

        self.client.force_login(user_a)
        response = self.client.get(reverse('recovery:case_list'))
        self.assertContains(response, 'pay_a')
        self.assertNotContains(response, 'pay_b')
        self.assertEqual(response.context['cases'].count(), 1)

        detail = self.client.get(reverse('recovery:case_detail', kwargs={'case_id': case_b.id}))
        self.assertEqual(detail.status_code, 404)

        dashboard = self.client.get(reverse('recovery:dashboard'))
        self.assertEqual(dashboard.context['total_cases'], 1)
