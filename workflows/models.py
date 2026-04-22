from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    class Actions(models.TextChoices):
        LOGIN = 'login', 'Login'
        SIGN = 'sign', 'Sign'
        APPROVE = 'approve', 'Approve'
        REJECT = 'reject', 'Reject'

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_events',
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_events',
    )
    action = models.CharField(max_length=20, choices=Actions.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Evento de auditoría'
        verbose_name_plural = 'Eventos de auditoría'

    def __str__(self):
        return f'{self.action} by {self.actor_id or "anonymous"}'
