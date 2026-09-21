from django.contrib import admin
from .models import Payment, PaymentEvent, Subscription


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('razorpay_payment_id', 'merchant', 'customer', 'amount_paise', 'currency', 'status', 'created_at')
    list_filter = ('status', 'currency', 'merchant', 'created_at')
    search_fields = ('razorpay_payment_id', 'customer__name', 'customer__email', 'description')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('razorpay_subscription_id', 'merchant', 'customer', 'status', 'plan_amount_paise', 'cycle_number')
    list_filter = ('status', 'merchant', 'created_at')
    search_fields = ('razorpay_subscription_id', 'plan_id', 'customer__name', 'customer__email')


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ('event_id', 'event_type', 'status', 'created_at', 'processed_at')
    list_filter = ('event_type', 'status', 'created_at')
    search_fields = ('event_id', 'event_type', 'error_message')
    readonly_fields = ('event_id', 'event_type', 'payload', 'status', 'error_message', 'created_at', 'processed_at')
