from django.contrib import admin
from .models import RecoveryCase

@admin.register(RecoveryCase)
class RecoveryCaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'payment', 'status', 'retries_attempted', 'updated_at')
    list_filter = ('status',)
    search_fields = ('id', 'payment__razorpay_payment_id')
