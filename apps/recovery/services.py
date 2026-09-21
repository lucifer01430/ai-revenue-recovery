from django.db import transaction
from django.utils import timezone
from apps.payments.models import Payment
from apps.merchants.models import Merchant
from apps.customers.models import Customer
from apps.recovery.models import (
    AIDiagnosis,
    AIRecommendation,
    AuthorizationChoices,
    ExecutionChoices,
    RecoveryAction,
    RecoveryActionChoices,
    RecoveryCase,
    RecoveryResult,
    ResultChoices,
    RecoveryPolicy,
    GuardrailIntervention,
)
from apps.audit.models import AuditLog
from apps.ai_engine.services import diagnose_and_recommend
from apps.guardrails.services import validate_action

def process_failed_payment(payment_entity, provider=None):
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
            defaults={
                "is_active": True,
                "razorpay_key_id": "rzp_test_placeholder",
                "razorpay_key_secret": "placeholder_secret",
                "email": "merchant@example.com",
            },
        )
        customer, _ = Customer.objects.get_or_create(
            merchant=merchant,
            email="test@example.com",
            defaults={"name": "Test User", "razorpay_customer_id": "cust_demo"},
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

        policy, _ = RecoveryPolicy.objects.get_or_create(merchant=merchant)

        # 3. DIAGNOSE & DECIDE (AI)
        ai_context = _build_ai_context(case, payment_entity, policy)
        ai_response = diagnose_and_recommend(ai_context, provider=provider)
        diagnosis = AIDiagnosis.objects.create(
            recovery_case=case,
            failure_category=ai_response['failure_category'],
            diagnosis=ai_response['reasoning_summary'],
            confidence=ai_response['confidence'],
            reasoning_summary=ai_response['reasoning_summary'],
        )
        recommendation = AIRecommendation.objects.create(
            diagnosis=diagnosis,
            recommended_action=ai_response['recommended_action'],
            suggested_timing=ai_response['suggested_timing'],
        )
        case.latest_diagnosis = ai_response['reasoning_summary']
        case.latest_recommendation = ai_response['recommended_action']
        case.save()
        
        AuditLog.objects.create(
            recovery_case_id=case.id,
            event_type="AI_DIAGNOSED",
            description=f"AI Recommendation: {ai_response['recommended_action']}. Diagnosis: {ai_response['reasoning_summary']}",
            metadata=ai_response
        )
        if ai_response.get('used_fallback'):
            AuditLog.objects.create(
                recovery_case_id=case.id,
                event_type="AI_FAILURE",
                description="AI provider failed or returned invalid output; fallback escalation applied.",
                metadata={"failure_reason": ai_response.get('failure_reason', 'Unknown provider failure')},
            )

        # 4. GUARD (Guardrails)
        guardrail_result = validate_action(case, recommendation.recommended_action)
        final_action = guardrail_result['modified_recommendation']

        GuardrailIntervention.objects.create(
            recovery_case=case,
            ai_recommendation=recommendation,
            original_action=recommendation.recommended_action,
            resulting_action=final_action,
            decision=guardrail_result['authorization_status'],
            reason_code=guardrail_result['reason_code'],
            reason=guardrail_result['reason'],
        )

        action = RecoveryAction.objects.create(
            recovery_case=case,
            ai_recommendation=recommendation,
            action_type=final_action,
            authorization_status=guardrail_result['authorization_status'],
        )
        
        AuditLog.objects.create(
            recovery_case_id=case.id,
            event_type="GUARDRAIL_EVALUATED",
            description=f"Guardrail decision: {guardrail_result['authorization_status']}. Final Action: {final_action}. Reason: {guardrail_result['reason']}",
            metadata=guardrail_result
        )

        if guardrail_result['authorization_status'] != AuthorizationChoices.APPROVED:
            action.execution_status = ExecutionChoices.BLOCKED
            action.save(update_fields=['execution_status', 'updated_at'])
            outcome = (
                ResultChoices.ESCALATED
                if guardrail_result['authorization_status'] == AuthorizationChoices.ESCALATED
                else ResultChoices.STOPPED
            )
            _record_result(case, action, outcome)
            return

        case.status = "ACTION_PENDING"
        case.save()

        # 5. ACT (Execution)
        execute_action(case, action)

def execute_action(case, recovery_action):
    """
    Executes the approved action.
    """
    if recovery_action.authorization_status != AuthorizationChoices.APPROVED:
        recovery_action.execution_status = ExecutionChoices.BLOCKED
        recovery_action.save(update_fields=['execution_status', 'updated_at'])
        return False

    action = recovery_action.action_type
    recovery_action.execution_status = ExecutionChoices.EXECUTED
    recovery_action.executed_at = timezone.now()
    recovery_action.save(update_fields=['execution_status', 'executed_at', 'updated_at'])

    if action == RecoveryActionChoices.RETRY_PAYMENT:
        case.retries_attempted += 1
        description = "Mocking a payment retry to Razorpay."
        if case.retries_attempted == 1:
            _record_result(case, recovery_action, ResultChoices.RECOVERED, case.payment.amount_paise)
            description += " Simulated payment outcome was SUCCESSFUL."
        else:
            _record_result(case, recovery_action, ResultChoices.PENDING_RESULT)
    elif action == RecoveryActionChoices.SEND_PAYMENT_LINK:
        description = "Generated and sent a payment link."
        _record_result(case, recovery_action, ResultChoices.PENDING_RESULT)
    elif action == RecoveryActionChoices.SEND_REMINDER:
        description = "Sent a payment recovery reminder."
        _record_result(case, recovery_action, ResultChoices.PENDING_RESULT)
    elif action == RecoveryActionChoices.SCHEDULE_RETRY:
        description = "Scheduled a payment retry."
        _record_result(case, recovery_action, ResultChoices.PENDING_RESULT)
    elif action == RecoveryActionChoices.ESCALATE_TO_HUMAN:
        description = "Escalated to human operator."
        case.status = "CLOSED"
        _record_result(case, recovery_action, ResultChoices.ESCALATED)
    elif action == RecoveryActionChoices.STOP_RECOVERY:
        description = "Stopped recovery based on policy."
        case.status = "CLOSED"
        _record_result(case, recovery_action, ResultChoices.STOPPED)

    case.save()

    AuditLog.objects.create(
        recovery_case_id=case.id,
        event_type="ACTION_EXECUTED",
        description=description,
        metadata={"action": action}
    )
    return True


def _record_result(case, recovery_action, status, recovered_amount_paise=None):
    """Persist the simulated/confirmed outcome before changing case status."""
    result = RecoveryResult.objects.create(
        recovery_case=case,
        recovery_action=recovery_action,
        status=status,
        recovered_amount_paise=recovered_amount_paise,
    )
    _apply_outcome_state(case, result)
    return result


def record_recovery_outcome(recovery_action, status, recovered_amount_paise=None, source='SIMULATION'):
    """Record a confirmed outcome once; pending outcomes may be completed later."""
    if recovery_action.authorization_status != AuthorizationChoices.APPROVED:
        return recovery_action.result if hasattr(recovery_action, 'result') else None, False
    if recovery_action.execution_status != ExecutionChoices.EXECUTED:
        return recovery_action.result if hasattr(recovery_action, 'result') else None, False
    if status not in ResultChoices.values:
        raise ValueError(f'Unsupported recovery outcome: {status}')

    with transaction.atomic():
        result = RecoveryResult.objects.select_for_update().filter(recovery_action=recovery_action).first()
        if result and result.status != ResultChoices.PENDING_RESULT:
            return result, False
        if result is None:
            result = RecoveryResult.objects.create(
                recovery_case=recovery_action.recovery_case,
                recovery_action=recovery_action,
                status=status,
                recovered_amount_paise=recovered_amount_paise,
            )
        else:
            result.status = status
            result.recovered_amount_paise = recovered_amount_paise
            result.save(update_fields=['status', 'recovered_amount_paise', 'updated_at'])
        _apply_outcome_state(recovery_action.recovery_case, result)
        AuditLog.objects.create(
            recovery_case_id=recovery_action.recovery_case_id,
            event_type='RECOVERY_OUTCOME_RECORDED',
            description=f'Recovery outcome {status} recorded from {source}.',
            metadata={'status': status, 'recovered_amount_paise': recovered_amount_paise, 'source': source},
        )
        return result, True


def _apply_outcome_state(case, result):
    """Keep payment and case state aligned with the persisted outcome."""
    if result.status == ResultChoices.RECOVERED:
        case.status = 'RECOVERED'
        case.payment.status = 'captured'
    elif result.status == ResultChoices.FAILED:
        case.status = 'FAILED'
        case.payment.status = 'failed'
    elif result.status in {ResultChoices.ESCALATED, ResultChoices.STOPPED}:
        case.status = 'CLOSED'
        case.payment.status = 'failed'
    elif result.status == ResultChoices.PENDING_RESULT:
        case.status = 'ACTION_PENDING'
    case.payment.save(update_fields=['status', 'updated_at'])
    case.save(update_fields=['status', 'updated_at'])
    AuditLog.objects.create(
        recovery_case_id=case.id,
        event_type='PAYMENT_OUTCOME_APPLIED',
        description=f'Payment outcome {result.status} applied to case.',
        metadata={'result_id': str(result.id), 'status': result.status},
    )


def _build_ai_context(case, payment_entity, policy):
    """Build the non-sensitive, provider-neutral context before inference."""
    payment = case.payment
    customer = payment.customer
    customer_payments = customer.payments.all()
    successful_payments = customer_payments.filter(status__in=['captured', 'success', 'paid'])
    failed_payments = customer_payments.filter(status='failed')
    last_success = successful_payments.order_by('-created_at').first()
    last_success_days = None
    if last_success:
        last_success_days = (timezone.now() - last_success.created_at).days

    last_action = case.recovery_actions.order_by('-created_at').first()
    last_result = case.recovery_results.order_by('-created_at').first()
    return {
        'case_id': str(case.id),
        'payment': {
            'id': payment.razorpay_payment_id,
            'amount': payment.amount_paise,
            'currency': payment.currency,
            'failure_reason': payment_entity.get('error_code', 'UNKNOWN'),
            'failure_description': payment.description or payment_entity.get('error_description', 'Payment failed'),
            'created_at': payment.created_at.isoformat(),
            'failed_at': payment.created_at.isoformat(),
        },
        'subscription': {
            'id': None,
            'status': None,
            'plan_amount': None,
            'cycle_number': None,
        },
        'customer': {
            'id': str(customer.id),
            'previous_successful_payments': successful_payments.count(),
            'previous_failed_payments': failed_payments.count(),
            'last_successful_payment_days_ago': last_success_days,
        },
        'recovery_history': {
            'total_attempts_on_this_case': case.recovery_actions.count(),
            'last_attempt_at': last_action.created_at.isoformat() if last_action else None,
            'last_attempt_action': last_action.action_type if last_action else None,
            'last_attempt_result': last_result.status if last_result else None,
        },
        'merchant_context': {
            'merchant_id': str(payment.merchant_id),
            'recovery_policy_summary': (
                f'max_retries={policy.max_retries_per_case}; '
                f'recovery_window_days={policy.recovery_window_days}; '
                f'high_value_threshold_paise={policy.high_value_threshold_paise}'
            ),
        },
    }
