import uuid
from django.db import models
from apps.payments.models import Payment

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
