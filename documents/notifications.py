from __future__ import annotations

import logging
from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _build_document_url(document_id: int) -> str:
    base_url = getattr(settings, 'PORTAL_BASE_URL', '').strip()
    path = f'/aprobaciones/{document_id}/'
    if not base_url:
        return path
    return urljoin(f'{base_url}/', path.lstrip('/'))


def _build_brand_logo_url() -> str:
    """
    URL absoluta del logo para correos (los clientes no resuelven {% static %}).
    """
    base_url = getattr(settings, 'PORTAL_BASE_URL', '').strip()
    static_path = 'static/portal/brand-logo.png?v=20260424c'
    if not base_url:
        return f'/{static_path}'
    return urljoin(f'{base_url}/', static_path)


def send_signatory_assignment_email(signatory) -> None:
    """
    Notifica por correo cuando un usuario es asignado como firmante.
    """
    if not getattr(settings, 'SIGNATORY_ASSIGNMENT_EMAIL_ENABLED', True):
        return

    recipient = (signatory.user.email or '').strip()
    if not recipient:
        logger.info(
            'Se omite notificación de firmante por email vacío. document_id=%s user_id=%s',
            signatory.document_id,
            signatory.user_id,
        )
        return

    document = signatory.document
    uploader = document.uploaded_by
    uploader_name = (uploader.get_full_name() or uploader.username).strip()
    recipient_name = (signatory.user.get_full_name() or signatory.user.username).strip()
    document_url = _build_document_url(document.id)
    brand_logo_url = _build_brand_logo_url()

    context = {
        'recipient_name': recipient_name,
        'document_title': document.title,
        'document_description': document.description,
        'assigned_by_name': uploader_name,
        'document_url': document_url,
        'brand_logo_url': brand_logo_url,
    }

    try:
        subject = f'Nuevo documento asignado para firma: {document.title}'
        text_body = render_to_string('emails/signatory_assigned.txt', context)
        html_body = render_to_string('emails/signatory_assigned.html', context)

        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            to=[recipient],
        )
        message.attach_alternative(html_body, 'text/html')
        message.send(fail_silently=False)
    except Exception:
        # El correo es un efecto secundario: no debe interrumpir el flujo de negocio.
        logger.exception(
            'Fallo al enviar notificación de firmante. document_id=%s user_id=%s recipient=%s',
            signatory.document_id,
            signatory.user_id,
            recipient,
        )

