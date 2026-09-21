from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'merchant', 'razorpay_customer_id', 'created_at')
    list_filter = ('merchant', 'created_at')
    search_fields = ('name', 'email', 'razorpay_customer_id')
