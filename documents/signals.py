from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DocumentSignatory
from .notifications import send_signatory_assignment_email


@receiver(post_save, sender=DocumentSignatory)
def notify_signatory_assignment(sender, instance: DocumentSignatory, created: bool, **kwargs):
    if not created:
        return

    # Evita envíos si la transacción principal falla/rollback.
    transaction.on_commit(lambda: send_signatory_assignment_email(instance))

