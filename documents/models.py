from django.conf import settings
from django.db import models


class Document(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SIGNED = 'signed', 'Signed'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='documents/')
    signed_file = models.FileField(upload_to='documents/signed/', blank=True, null=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requires_signature = models.BooleanField(default=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='archived_documents',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'

    def current_pending_signatory(self):
        return self.signatories.filter(status=DocumentSignatory.Status.PENDING).order_by('sign_order', 'id').first()

    def rejected_signatory(self):
        return self.signatories.filter(status=DocumentSignatory.Status.REJECTED).select_related('user').order_by('rejected_at', 'id').first()


class DocumentSignatory(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SIGNED = 'signed', 'Signed'
        REJECTED = 'rejected', 'Rejected'

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='signatories')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='document_signatories')
    sign_order = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.TextField(blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('document', 'user')
        constraints = [
            models.UniqueConstraint(fields=('document', 'sign_order'), name='uniq_document_sign_order'),
        ]
        ordering = ('sign_order', 'id')
        verbose_name = 'Firmante del documento'
        verbose_name_plural = 'Firmantes del documento'

    def __str__(self):
        return f'{self.user} -> {self.document}'
