from django.test import TestCase

from .admin import AuditLogAdmin
from .models import AuditLog


class AuditLogAdminTests(TestCase):
    def test_audit_log_is_read_only_in_admin(self):
        model_admin = AuditLogAdmin(AuditLog, None)

        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None))
        self.assertFalse(model_admin.has_delete_permission(None))
