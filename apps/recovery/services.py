from django.db import transaction
from apps.payments.models import Payment
from apps.merchants.models import Merchant
from apps.customers.models import Customer
from apps.recovery.models import RecoveryCase
from apps.audit.models import AuditLog
from apps.ai_engine.services import diagnose_and_recommend
from apps.guardrails.services import validate_action

def process_failed_payment(payment_entity):
    """
    The main orchestrator for the recovery workflow.
    """
    razorpay_payment_id = payment_entity.get('id', 'pay_dummy')
    amount = payment_entity.get('amount', 1000)
    currency = payment_entity.get('currency', 'INR')
    error_code = payment_entity.get('error_code', 'UNKNOWN')
    error_description = payment_entity.get('error_description', 'Payment failed')
    
    with transaction.atomic():
        # 1. Setup Data (Get or Create)
        merchant, _ = Merchant.objects.get_or_create(
            name="Demo Merchant",
            defaults={"is_active": True}
        )
        customer, _ = Customer.objects.get_or_create(
            merchant=merchant,
            email="test@example.com",
            defaults={"name": "Test User"}
        )
        payment, created = Payment.objects.get_or_create(
            razorpay_payment_id=razorpay_payment_id,
            merchant=merchant,
            defaults={
                "customer": customer,
                "amount_paise": amount,
                "currency": currency,
                "status": "failed",
                "description": error_description
            }
        )
        
        # 2. DETECT -> Create Recovery Case
        case, case_created = RecoveryCase.objects.get_or_create(
            payment=payment,
            defaults={"status": "OPEN"}
        )
        if case_created:
            AuditLog.objects.create(
                recovery_case_id=case.id,
                event_type="CASE_CREATED",
                description=f"Recovery case opened for payment {razorpay_payment_id}."
            )
        
        case.status = "DIAGNOSING"
        case.save()

        # 3. DIAGNOSE & DECIDE (AI)
        ai_response = diagnose_and_recommend({
            "error_code": error_code,
            "error_description": error_description
        })
        case.latest_diagnosis = ai_response['diagnosis']
        case.latest_recommendation = ai_response['recommendation']
        case.save()
        
        AuditLog.objects.create(
            recovery_case_id=case.id,
            event_type="AI_DIAGNOSED",
            description=f"AI Recommendation: {ai_response['recommendation']}. Diagnosis: {ai_response['diagnosis']}",
            metadata=ai_response
        )

        # 4. GUARD (Guardrails)
        guardrail_result = validate_action(case, ai_response['recommendation'])
        final_action = guardrail_result['modified_recommendation']
        
        AuditLog.objects.create(
            recovery_case_id=case.id,
            event_type="GUARDRAIL_EVALUATED",
            description=f"Guardrail approved: {guardrail_result['approved']}. Final Action: {final_action}. Reason: {guardrail_result['reason']}",
            metadata=guardrail_result
        )

        case.status = "ACTION_PENDING"
        case.save()

        # 5. ACT (Execution)
        execute_action(case, final_action)

def execute_action(case, action):
    """
    Executes the approved action.
    """
    if action == 'retry':
        case.retries_attempted += 1
        description = "Mocking a payment retry to Razorpay."
        # In a real scenario, this is where we call Razorpay API.
        
    elif action == 'payment_link':
        description = "Generated and sent a payment link."
    elif action == 'escalate':
        description = "Escalated to human operator."
        case.status = "CLOSED"
    elif action == 'stop':
        description = "Stopped recovery based on policy."
        case.status = "CLOSED"
    else:
        description = f"Executed unknown action: {action}"
    
    # Wait, let's say a successful retry makes status RECOVERED for demo
    if action == 'retry' and case.retries_attempted == 1:
        # Mock success on first retry for happy path demo
        case.status = "RECOVERED"
        description += " Retry was SUCCESSFUL."

    case.save()

    AuditLog.objects.create(
        recovery_case_id=case.id,
        event_type="ACTION_EXECUTED",
        description=description,
        metadata={"action": action}
    )
