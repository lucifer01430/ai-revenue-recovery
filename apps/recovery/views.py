from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import RecoveryCase
from apps.audit.models import AuditLog
from .models import GuardrailIntervention, RecoveryResult, ResultChoices, AuthorizationChoices
from apps.merchants.views import merchant_for_user

@login_required
def dashboard(request):
    merchant = merchant_for_user(request.user)
    if not merchant:
        from django.shortcuts import redirect
        return redirect('merchant_setup')
    # Total failed payments (Cases created)
    cases = RecoveryCase.objects.filter(payment__merchant=merchant)
    total_cases = cases.count()
    
    open_cases = cases.filter(status__in=['OPEN', 'DIAGNOSING', 'ACTION_PENDING']).count()
    revenue_at_risk_paise = cases.aggregate(total=Sum('payment__amount_paise'))['total'] or 0
    results = RecoveryResult.objects.filter(recovery_case__payment__merchant=merchant)
    revenue_recovered_paise = results.filter(status=ResultChoices.RECOVERED).aggregate(total=Sum('recovered_amount_paise'))['total'] or 0
    revenue_recovered = revenue_recovered_paise / 100.0
    successful_recoveries = results.filter(status=ResultChoices.RECOVERED).count()
    failed_recoveries = results.filter(status=ResultChoices.FAILED).count()
    guardrail_blocks = GuardrailIntervention.objects.filter(
        recovery_case__payment__merchant=merchant,
        decision=AuthorizationChoices.REJECTED,
    ).count()
    human_escalations = results.filter(status=ResultChoices.ESCALATED).count()
    ai_fallbacks = AuditLog.objects.filter(
        recovery_case_id__in=cases.values('id'), event_type='AI_FAILURE'
    ).count()
    recovery_rate = (revenue_recovered_paise / revenue_at_risk_paise * 100) if revenue_at_risk_paise else 0

    context = {
        'total_cases': total_cases,
        'recovered_cases': successful_recoveries,
        'closed_cases': human_escalations,
        'open_cases': open_cases,
        'failed_cases': failed_recoveries,
        'revenue_at_risk': revenue_at_risk_paise / 100.0,
        'revenue_recovered': revenue_recovered,
        'recovery_rate': round(recovery_rate, 2),
        'successful_recoveries': successful_recoveries,
        'failed_recoveries': failed_recoveries,
        'guardrail_blocks': guardrail_blocks,
        'human_escalations': human_escalations,
        'ai_fallbacks': ai_fallbacks,
        'merchant': merchant,
        'recent_cases': cases.select_related('payment', 'payment__customer').order_by('-created_at')[:5]
    }
    return render(request, 'recovery/dashboard.html', context)

@login_required
def case_list(request):
    merchant = merchant_for_user(request.user)
    if not merchant:
        from django.shortcuts import redirect
        return redirect('merchant_setup')
    cases = RecoveryCase.objects.filter(payment__merchant=merchant).select_related(
        'payment', 'payment__customer'
    ).order_by('-created_at')
    return render(request, 'recovery/case_list.html', {'cases': cases, 'merchant': merchant})

@login_required
def case_detail(request, case_id):
    merchant = merchant_for_user(request.user)
    if not merchant:
        from django.shortcuts import redirect
        return redirect('merchant_setup')
    case = get_object_or_404(
        RecoveryCase.objects.select_related('payment', 'payment__customer'),
        id=case_id,
        payment__merchant=merchant,
    )
    audit_logs = AuditLog.objects.filter(recovery_case_id=case.id).order_by('created_at')
    
    return render(request, 'recovery/case_detail.html', {
        'case': case,
        'audit_logs': audit_logs,
        'merchant': merchant,
    })
