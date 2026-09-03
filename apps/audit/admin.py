from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'recovery_case_id', 'created_at')
    search_fields = ('event_type', 'recovery_case_id')
    list_filter = ('event_type', 'created_at')
