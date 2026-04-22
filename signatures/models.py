from django.conf import settings
from django.db import models


class Signature(models.Model):
    document = models.ForeignKey('documents.Document', on_delete=models.CASCADE, related_name='signatures')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='signatures')
    signed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    signature_data = models.TextField()
    is_valid = models.BooleanField(default=True)

    class Meta:
        ordering = ('-signed_at',)
        unique_together = ('document', 'user')
