import uuid
from django.db import models
from apps.merchants.models import Merchant
from apps.customers.models import Customer

class Payment(models.Model):
    """
    A single payment record.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='payments')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payments')
    razorpay_payment_id = models.CharField(max_length=100)
    amount_paise = models.IntegerField()
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['merchant', 'razorpay_payment_id'], name='unique_payment_per_merchant')
        ]
        indexes = [
            models.Index(fields=['merchant', 'status']),
            models.Index(fields=['razorpay_payment_id']),
            models.Index(fields=['customer', 'status']),
        ]

    def __str__(self):
        return f"Payment {self.razorpay_payment_id} - {self.status}"

class Subscription(models.Model):
    """
    A recurring subscription associated with a customer.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='subscriptions')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='subscriptions')
    razorpay_subscription_id = models.CharField(max_length=100)
    plan_id = models.CharField(max_length=100)
    status = models.CharField(max_length=50)
    plan_amount_paise = models.IntegerField()
    cycle_number = models.IntegerField(default=1)
    current_start = models.DateTimeField(blank=True, null=True)
    current_end = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['merchant', 'razorpay_subscription_id'], name='unique_subscription_per_merchant')
        ]
        indexes = [
            models.Index(fields=['merchant', 'status']),
            models.Index(fields=['razorpay_subscription_id']),
            models.Index(fields=['customer', 'status']),
        ]

    def __str__(self):
        return f"Subscription {self.razorpay_subscription_id} - {self.status}"
