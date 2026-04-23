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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'


class DocumentSignatory(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SIGNED = 'signed', 'Signed'

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='signatories')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='document_signatories')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('document', 'user')
        ordering = ('id',)
        verbose_name = 'Firmante del documento'
        verbose_name_plural = 'Firmantes del documento'

    def __str__(self):
        return f'{self.user} -> {self.document}'
