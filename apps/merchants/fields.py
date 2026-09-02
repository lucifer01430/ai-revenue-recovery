import base64
from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken

def get_fernet():
    key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
    if not key:
        # Fallback for dev only. In production, provide 32-urlsafe-base64-encoded bytes
        key = base64.urlsafe_b64encode(b'dev-fallback-key-must-be-32-byte')
    return Fernet(key)

class EncryptedCharField(models.CharField):
    """
    A simple Django model field that encrypts data before saving to the DB,
    and decrypts it when retrieving.
    """
    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if not value:
            return value
        fernet = get_fernet()
        # Encrypt the string and return as a string
        return fernet.encrypt(value.encode('utf-8')).decode('utf-8')

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        fernet = get_fernet()
        try:
            return fernet.decrypt(value.encode('utf-8')).decode('utf-8')
        except InvalidToken:
            return value
