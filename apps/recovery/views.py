from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, Count
from .models import RecoveryCase
from apps.payments.models import Payment
from apps.audit.models import AuditLog

def dashboard(request):
    # Total failed payments (Cases created)
    total_cases = RecoveryCase.objects.count()
    
    # Cases recovered
    recovered_cases = RecoveryCase.objects.filter(status='RECOVERED').count()
    
    # Escalate / Stop / Unresolved
    closed_cases = RecoveryCase.objects.filter(status='CLOSED').count()
    open_cases = RecoveryCase.objects.filter(status__in=['OPEN', 'DIAGNOSING', 'ACTION_PENDING']).count()
    failed_cases = RecoveryCase.objects.filter(status='FAILED').count()
    
    # Revenue metrics
    # Revenue at risk: Sum of amount_paise for all cases
    revenue_at_risk_paise = RecoveryCase.objects.aggregate(total=Sum('payment__amount_paise'))['total'] or 0
    revenue_at_risk = revenue_at_risk_paise / 100.0

    # Revenue recovered: Sum of amount_paise for RECOVERED cases
    revenue_recovered_paise = RecoveryCase.objects.filter(status='RECOVERED').aggregate(total=Sum('payment__amount_paise'))['total'] or 0
    revenue_recovered = revenue_recovered_paise / 100.0

    recovery_rate = (recovered_cases / total_cases * 100) if total_cases > 0 else 0

    context = {
        'total_cases': total_cases,
        'recovered_cases': recovered_cases,
        'closed_cases': closed_cases,
        'open_cases': open_cases,
        'failed_cases': failed_cases,
        'revenue_at_risk': revenue_at_risk,
        'revenue_recovered': revenue_recovered,
        'recovery_rate': round(recovery_rate, 2),
        'recent_cases': RecoveryCase.objects.select_related('payment', 'payment__customer').order_by('-created_at')[:5]
    }
    return render(request, 'recovery/dashboard.html', context)

def case_list(request):
    cases = RecoveryCase.objects.select_related('payment', 'payment__customer').order_by('-created_at')
    return render(request, 'recovery/case_list.html', {'cases': cases})

def case_detail(request, case_id):
    case = get_object_or_404(RecoveryCase.select_related('payment', 'payment__customer'), id=case_id)
    audit_logs = AuditLog.objects.filter(recovery_case_id=case.id).order_by('created_at')
    
    return render(request, 'recovery/case_detail.html', {
        'case': case,
        'audit_logs': audit_logs,
    })
