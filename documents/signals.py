import logging
import threading
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DocumentSignatory
from .notifications import send_signatory_assignment_email

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DocumentSignatory)
def notify_signatory_assignment(sender, instance: DocumentSignatory, created: bool, **kwargs):
    if not created:
        return

    # Evita envíos si la transacción principal falla/rollback.
    def _send_notification():
        try:
            send_signatory_assignment_email(instance)
        except Exception:
            # Defensa adicional: jamás bloquear la transacción ya confirmada.
            logger.exception(
                'Fallo inesperado en callback de notificación. document_id=%s user_id=%s',
                instance.document_id,
                instance.user_id,
            )

    # No bloquea la respuesta HTTP por latencia SMTP.
    transaction.on_commit(lambda: threading.Thread(target=_send_notification, daemon=True).start())

