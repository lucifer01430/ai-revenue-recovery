import uuid
from django.db import models
from apps.payments.models import Payment
from apps.merchants.models import Merchant


class RecoveryActionChoices(models.TextChoices):
    RETRY_PAYMENT = 'RETRY_PAYMENT', 'Retry payment'
    SEND_PAYMENT_LINK = 'SEND_PAYMENT_LINK', 'Send payment link'
    SEND_REMINDER = 'SEND_REMINDER', 'Send reminder'
    SCHEDULE_RETRY = 'SCHEDULE_RETRY', 'Schedule retry'
    ESCALATE_TO_HUMAN = 'ESCALATE_TO_HUMAN', 'Escalate to human'
    STOP_RECOVERY = 'STOP_RECOVERY', 'Stop recovery'


class FailureCategoryChoices(models.TextChoices):
    INSUFFICIENT_FUNDS = 'INSUFFICIENT_FUNDS', 'Insufficient funds'
    CARD_EXPIRED = 'CARD_EXPIRED', 'Card expired'
    BANK_DECLINED = 'BANK_DECLINED', 'Bank declined'
    NETWORK_ERROR = 'NETWORK_ERROR', 'Network error'
    PAYMENT_METHOD_INVALID = 'PAYMENT_METHOD_INVALID', 'Payment method invalid'
    CUSTOMER_INITIATED_FAILURE = 'CUSTOMER_INITIATED_FAILURE', 'Customer initiated failure'
    UNKNOWN = 'UNKNOWN', 'Unknown'


class ConfidenceChoices(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'


class TimingChoices(models.TextChoices):
    IMMEDIATE = 'IMMEDIATE', 'Immediate'
    AFTER_24H = 'AFTER_24H', 'After 24 hours'
    AFTER_48H = 'AFTER_48H', 'After 48 hours'
    NOT_APPLICABLE = 'NOT_APPLICABLE', 'Not applicable'


class AuthorizationChoices(models.TextChoices):
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    ESCALATED = 'ESCALATED', 'Escalated'


class ExecutionChoices(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    EXECUTED = 'EXECUTED', 'Executed'
    FAILED = 'FAILED', 'Failed'
    BLOCKED = 'BLOCKED', 'Blocked'


class ResultChoices(models.TextChoices):
    RECOVERED = 'RECOVERED', 'Recovered'
    FAILED = 'FAILED', 'Failed'
    ESCALATED = 'ESCALATED', 'Escalated'
    STOPPED = 'STOPPED', 'Stopped'
    PENDING_RESULT = 'PENDING_RESULT', 'Pending result'

class RecoveryCase(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('DIAGNOSING', 'Diagnosing'),
        ('ACTION_PENDING', 'Action Pending'),
        ('RECOVERED', 'Recovered'),
        ('FAILED', 'Failed'),
        ('CLOSED', 'Closed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='recovery_case')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    retries_attempted = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Store the latest AI decision and reasoning
    latest_diagnosis = models.TextField(blank=True, null=True)
    latest_recommendation = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"Case {self.id} for Payment {self.payment.razorpay_payment_id}"


class AIDiagnosis(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recovery_case = models.ForeignKey(RecoveryCase, on_delete=models.CASCADE, related_name='ai_diagnoses')
    failure_category = models.CharField(max_length=40, choices=FailureCategoryChoices.choices)
    diagnosis = models.TextField()
    confidence = models.CharField(max_length=10, choices=ConfidenceChoices.choices)
    reasoning_summary = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.failure_category} diagnosis for {self.recovery_case_id}"


class AIRecommendation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    diagnosis = models.ForeignKey(AIDiagnosis, on_delete=models.CASCADE, related_name='recommendations')
    recommended_action = models.CharField(max_length=30, choices=RecoveryActionChoices.choices)
    suggested_timing = models.CharField(max_length=20, choices=TimingChoices.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def recovery_case(self):
        return self.diagnosis.recovery_case

    def __str__(self):
        return f"{self.recommended_action} for {self.diagnosis.recovery_case_id}"


class RecoveryPolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.OneToOneField(Merchant, on_delete=models.CASCADE, related_name='recovery_policy')
    max_retries_per_case = models.PositiveSmallIntegerField(default=3)
    recovery_window_days = models.PositiveSmallIntegerField(default=7)
    duplicate_action_cooldown_hours = models.PositiveSmallIntegerField(default=24)
    high_value_threshold_paise = models.PositiveIntegerField(default=50000)
    escalation_failure_threshold = models.PositiveSmallIntegerField(default=2)
    no_retry_on_fraud = models.BooleanField(default=True)
    abandonment_timeout_days = models.PositiveSmallIntegerField(default=14)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Recovery policy for {self.merchant.name}"


class GuardrailIntervention(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recovery_case = models.ForeignKey(RecoveryCase, on_delete=models.CASCADE, related_name='guardrail_interventions')
    ai_recommendation = models.ForeignKey(AIRecommendation, on_delete=models.SET_NULL, null=True, blank=True, related_name='guardrail_interventions')
    original_action = models.CharField(max_length=30, choices=RecoveryActionChoices.choices)
    resulting_action = models.CharField(max_length=30, choices=RecoveryActionChoices.choices)
    decision = models.CharField(max_length=10, choices=AuthorizationChoices.choices)
    reason_code = models.CharField(max_length=60)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.decision}: {self.reason_code}"


class RecoveryAction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recovery_case = models.ForeignKey(RecoveryCase, on_delete=models.CASCADE, related_name='recovery_actions')
    ai_recommendation = models.ForeignKey(AIRecommendation, on_delete=models.SET_NULL, null=True, blank=True, related_name='recovery_actions')
    action_type = models.CharField(max_length=30, choices=RecoveryActionChoices.choices)
    authorization_status = models.CharField(max_length=10, choices=AuthorizationChoices.choices)
    execution_status = models.CharField(max_length=10, choices=ExecutionChoices.choices, default=ExecutionChoices.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action_type} for {self.recovery_case_id}"


class RecoveryResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recovery_case = models.ForeignKey(RecoveryCase, on_delete=models.CASCADE, related_name='recovery_results')
    recovery_action = models.OneToOneField(RecoveryAction, on_delete=models.CASCADE, related_name='result')
    status = models.CharField(max_length=20, choices=ResultChoices.choices)
    recovered_amount_paise = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.status} result for {self.recovery_case_id}"
