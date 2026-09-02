import uuid
from django.db import models
from apps.merchants.models import Merchant

class Customer(models.Model):
    """
    A customer of a merchant. Not a platform user.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='customers')
    razorpay_customer_id = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['merchant', 'razorpay_customer_id'], name='unique_customer_per_merchant')
        ]
        indexes = [
            models.Index(fields=['merchant', 'email']),
            models.Index(fields=['razorpay_customer_id']),
        ]

    def __str__(self):
        return f"{self.name} ({self.merchant.name})"
