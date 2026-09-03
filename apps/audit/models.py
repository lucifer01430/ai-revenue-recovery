from django.db import models
import uuid

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recovery_case_id = models.UUIDField(null=True, blank=True)
    event_type = models.CharField(max_length=50) # e.g., CASE_CREATED, AI_DIAGNOSED, GUARDRAIL_BLOCKED, ACTION_EXECUTED
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} - {self.created_at}"
