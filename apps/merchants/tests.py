from django.conf import settings
from django.core import mail
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

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
        user = self.make_user('login_user')
        self.assertFalse(self.client.login(username='login_user', password='wrong'))
        self.make_merchant(user, 'Login Business')
        response = self.client.post(reverse('login'), {'username': 'login_user', 'password': 'safe-pass-123'})
        self.assertRedirects(response, '/app/')

    def test_public_root_is_available_without_authentication(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AI Revenue Recovery')

    def test_protected_routes_redirect_unauthenticated_users(self):
        for url in ('/app/', '/app/cases/', '/app/cases/00000000-0000-0000-0000-000000000001/'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login/', response.url)

    def test_user_without_merchant_is_sent_to_setup(self):
        user = self.make_user('needs_setup')
        self.client.force_login(user)
        response = self.client.get('/app/')
        self.assertRedirects(response, reverse('merchant_setup'))

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

    def test_logout_works(self):
        user = self.make_user('logout_user')
        self.make_merchant(user, 'Logout Business')
        self.client.force_login(user)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
        self.assertFalse('_auth_user_id' in self.client.session)

    @override_settings(MAILERS={'default': {'BACKEND': 'django.core.mail.backends.locmem.EmailBackend'}})
    def test_password_reset_flow_uses_django_token_views(self):
        user = self.make_user('reset_user')
        user.email = 'reset@example.com'
        user.save(update_fields=['email'])
        response = self.client.post(reverse('password_reset'), {'email': user.email})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        response = self.client.post(reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token}), {})
        self.assertRedirects(response, f'/reset/{uid}/set-password/')
        response = self.client.post(response.url, {
            'new_password1': 'new-safe-pass-123',
            'new_password2': 'new-safe-pass-123',
        })
        self.assertRedirects(response, reverse('password_reset_complete'))
        self.assertTrue(self.client.login(username='reset_user', password='new-safe-pass-123'))

    def test_authenticated_password_change_route_is_protected(self):
        user = self.make_user('change_user')
        response = self.client.get(reverse('password_change'))
        self.assertRedirects(response, f'{reverse("login")}?next={reverse("password_change")}')
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('password_change')).status_code, 200)

    def test_admin_routes_remain_available(self):
        response = self.client.get('/admin/login/')
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/admin/')
        self.assertIn(response.status_code, (301, 302))

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

    def test_recovery_case_detail_renders_workflow(self):
        user = self.make_user('workflow_owner')
        merchant = self.make_merchant(user, 'Workflow Business')
        case = self.make_case(merchant, 'workflow')
        self.client.force_login(user)
        response = self.client.get(reverse('recovery:case_detail', kwargs={'case_id': case.id}))
        self.assertEqual(response.status_code, 200)
        for step in ('Detect', 'Diagnose', 'Decide', 'Guard', 'Act', 'Recover', 'Measure', 'Audit'):
            self.assertContains(response, step)
        self.assertContains(response, 'pay_workflow')
