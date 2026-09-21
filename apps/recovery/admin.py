from django.contrib import admin
from .models import (
    AIDiagnosis,
    AIRecommendation,
    GuardrailIntervention,
    RecoveryAction,
    RecoveryCase,
    RecoveryPolicy,
    RecoveryResult,
)

@admin.register(RecoveryCase)
class RecoveryCaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'payment', 'status', 'retries_attempted', 'updated_at')
    list_filter = ('status',)
    search_fields = ('id', 'payment__razorpay_payment_id')


@admin.register(AIDiagnosis)
class AIDiagnosisAdmin(admin.ModelAdmin):
    list_display = ('recovery_case', 'failure_category', 'confidence', 'created_at')
    list_filter = ('failure_category', 'confidence', 'created_at')
    search_fields = ('recovery_case__id', 'diagnosis', 'reasoning_summary')


@admin.register(AIRecommendation)
class AIRecommendationAdmin(admin.ModelAdmin):
    list_display = ('diagnosis', 'recommended_action', 'suggested_timing', 'created_at')
    list_filter = ('recommended_action', 'suggested_timing', 'created_at')
    search_fields = ('diagnosis__recovery_case__id', 'recommended_action')


@admin.register(RecoveryPolicy)
class RecoveryPolicyAdmin(admin.ModelAdmin):
    list_display = ('merchant', 'max_retries_per_case', 'recovery_window_days', 'high_value_threshold_paise', 'updated_at')
    list_filter = ('no_retry_on_fraud', 'recovery_window_days')
    search_fields = ('merchant__name', 'merchant__email')


@admin.register(GuardrailIntervention)
class GuardrailInterventionAdmin(admin.ModelAdmin):
    list_display = ('recovery_case', 'original_action', 'resulting_action', 'decision', 'reason_code', 'created_at')
    list_filter = ('decision', 'reason_code', 'created_at')
    search_fields = ('recovery_case__id', 'reason_code', 'reason')


@admin.register(RecoveryAction)
class RecoveryActionAdmin(admin.ModelAdmin):
    list_display = ('recovery_case', 'action_type', 'authorization_status', 'execution_status', 'executed_at', 'created_at')
    list_filter = ('action_type', 'authorization_status', 'execution_status', 'created_at')
    search_fields = ('recovery_case__id', 'action_type')


@admin.register(RecoveryResult)
class RecoveryResultAdmin(admin.ModelAdmin):
    list_display = ('recovery_case', 'recovery_action', 'status', 'recovered_amount_paise', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('recovery_case__id', 'recovery_action__id')
