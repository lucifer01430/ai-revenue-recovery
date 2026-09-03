import time
from django.core.management.base import BaseCommand
from apps.recovery.services import process_failed_payment
from apps.recovery.models import RecoveryCase
from apps.audit.models import AuditLog

class Command(BaseCommand):
    help = 'Simulates a Razorpay payment.failed event and traces the recovery flow.'

    def add_arguments(self, parser):
        parser.add_argument('--error', type=str, default='BAD_REQUEST_ERROR', help='Error code to simulate')
        parser.add_argument('--desc', type=str, default='Payment failed due to insufficient funds', help='Error description to simulate')
        parser.add_argument('--amount', type=int, default=250000, help='Amount in paise')

    def handle(self, *args, **options):
        error_code = options['error']
        error_description = options['desc']
        amount = options['amount']
        
        # A realistic-looking Razorpay payment entity mock
        payment_id = f"pay_sim_{int(time.time())}"
        
        mock_payment_entity = {
            'id': payment_id,
            'entity': 'payment',
            'amount': amount,
            'currency': 'INR',
            'status': 'failed',
            'order_id': f"order_sim_{int(time.time())}",
            'invoice_id': None,
            'international': False,
            'method': 'card',
            'amount_refunded': 0,
            'refund_status': None,
            'captured': False,
            'description': error_description,
            'card_id': 'card_12345',
            'error_code': error_code,
            'error_description': error_description,
            'error_source': 'issuer',
            'error_step': 'payment_authorization',
            'error_reason': 'payment_failed'
        }

        self.stdout.write(self.style.WARNING(f"\n[1] DETECT: Simulated incoming webhook for {payment_id}"))
        self.stdout.write(f"    Reason: {error_description}")

        # Trigger the flow
        process_failed_payment(mock_payment_entity)

        # Retrieve the case and print the audit trace
        try:
            case = RecoveryCase.objects.get(payment__razorpay_payment_id=payment_id)
            
            self.stdout.write(self.style.SUCCESS(f"\n[2] Flow execution completed. Case ID: {case.id}"))
            self.stdout.write(self.style.SUCCESS(f"    Final Status: {case.status}"))
            self.stdout.write(f"    AI Diagnosis: {case.latest_diagnosis}")
            self.stdout.write(f"    AI Recommendation: {case.latest_recommendation}")

            self.stdout.write(self.style.WARNING("\n--- AUDIT TRAIL ---"))
            logs = AuditLog.objects.filter(recovery_case_id=case.id).order_by('created_at')
            for idx, log in enumerate(logs, 1):
                self.stdout.write(f"{idx}. [{log.event_type}] {log.description}")
            
            self.stdout.write(self.style.WARNING("-------------------\n"))
            self.stdout.write("Test completed successfully! Run again to simulate another failure.")

        except RecoveryCase.DoesNotExist:
            self.stdout.write(self.style.ERROR("Error: RecoveryCase was not created."))
