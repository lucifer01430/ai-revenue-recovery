import uuid
from django.db import models
from .fields import EncryptedCharField

class Merchant(models.Model):
    """
    Represents a business using the platform.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    razorpay_key_id = models.CharField(max_length=100)
    razorpay_key_secret = EncryptedCharField(max_length=255)
    email = models.EmailField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
