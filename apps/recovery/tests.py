from django.test import TestCase
from apps.recovery.services import process_failed_payment
from apps.recovery.models import RecoveryCase
from apps.audit.models import AuditLog

class RecoveryFlowTestCase(TestCase):
    def test_end_to_end_recovery_flow(self):
        # 1. Simulate webhook payload for failed payment
        mock_payment_entity = {
            'id': 'pay_failed_12345',
            'amount': 250000, # 2500 INR
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
        self.assertEqual(case.latest_recommendation, 'retry')
        
        # Check Audit Logs
        logs = AuditLog.objects.filter(recovery_case_id=case.id).order_by('created_at')
        self.assertEqual(logs.count(), 4)
        
        event_types = [log.event_type for log in logs]
        self.assertEqual(event_types, [
            'CASE_CREATED',
            'AI_DIAGNOSED',
            'GUARDRAIL_EVALUATED',
            'ACTION_EXECUTED'
        ])
        
        print("\n\n--- SUCCESS: E2E Recovery Flow Tested Successfully ---")
        for log in logs:
            print(f"[{log.event_type}] {log.description}")
        print("------------------------------------------------------\n")
