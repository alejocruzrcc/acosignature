from __future__ import annotations

import base64
import re
from io import BytesIO
from types import SimpleNamespace
from typing import Any, List, Tuple

from django.core.files.base import ContentFile
from django.utils import timezone as django_timezone
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def _decode_data_url(data_url: str) -> Tuple[bytes, str]:
    """
    Convierte data URL (base64) a bytes y mime type.
    """
    if not data_url or ',' not in data_url:
        raise ValueError('Firma inválida: formato data URL no reconocido.')

    header, payload = data_url.split(',', 1)
    mime_match = re.match(r'data:(.*?);base64$', header)
    mime_type = mime_match.group(1) if mime_match else 'image/png'
    return base64.b64decode(payload), mime_type


def _render_signatures_pdf_bytes(signatures: List[Any], document_title: str) -> bytes:
    """
    Construye una o más páginas de firmas. Cada elemento de `signatures` debe tener:
    user, signature_data (data URL), signed_at (datetime).
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    margin_x = 48
    margin_y = 42

    c.setTitle(f'Firmas - {document_title}')
    y = height - margin_y
    c.setFont('Helvetica-Bold', 14)
    c.drawString(margin_x, y, 'Hoja de firmas')
    y -= 24

    row_height = 142
    signature_box_w = 200
    signature_box_h = 72

    for idx, sig in enumerate(signatures, start=1):
        if y - row_height < margin_y:
            c.showPage()
            y = height - margin_y
            c.setFont('Helvetica-Bold', 14)
            c.drawString(margin_x, y, 'Hoja de firmas (continuación)')
            y -= 28

        user = sig.user
        full_name = (user.get_full_name() or user.username).strip()
        cargo = (user.cargo or 'N/D').strip()
        doc_number = user.document_number or 'N/D'

        c.setFont('Helvetica-Bold', 11)
        c.drawString(margin_x, y, f'Firmante #{idx}')
        y -= 16

        c.setFont('Helvetica', 10)
        c.drawString(margin_x, y, f'Nombre: {full_name}')
        y -= 14
        c.drawString(margin_x, y, f'Cargo: {cargo}')
        y -= 14
        c.drawString(margin_x, y, f'Documento: {doc_number}')
        y -= 14
        c.drawString(margin_x, y, f'Fecha firma: {sig.signed_at.strftime("%Y-%m-%d %H:%M:%S UTC")}')
        y -= 8

        c.rect(margin_x, y - signature_box_h, signature_box_w, signature_box_h, stroke=1, fill=0)
        try:
            img_bytes, _mime = _decode_data_url(sig.signature_data)
            img_reader = ImageReader(BytesIO(img_bytes))
            c.drawImage(
                img_reader,
                margin_x + 6,
                y - signature_box_h + 6,
                width=signature_box_w - 12,
                height=signature_box_h - 12,
                preserveAspectRatio=True,
                anchor='c',
                mask='auto',
            )
        except Exception:
            c.setFont('Helvetica-Oblique', 9)
            c.drawString(margin_x + 8, y - signature_box_h + 8, 'No se pudo renderizar la imagen de firma')

        y -= row_height

    c.save()
    return buf.getvalue()


def _build_signatures_page(document) -> bytes:
    """
    Construye una o más páginas de firmas con las firmas ya guardadas en BD.
    """
    signatures = list(document.signatures.select_related('user').order_by('signed_at', 'id'))
    return _render_signatures_pdf_bytes(signatures, document.title)


def build_signed_pdf_preview_bytes(document, pending_user, pending_signature_data: str) -> bytes:
    """
    PDF en memoria: documento original + hoja de firmas como quedaría al registrar
    la firma pendiente del usuario (sin persistir cambios).
    """
    if not document.file:
        raise ValueError('El documento no tiene archivo base.')
    if not document.file.name or not document.file.storage.exists(document.file.name):
        raise ValueError('No se encontró el archivo base del documento en el almacenamiento.')

    existing = list(document.signatures.select_related('user').order_by('signed_at', 'id'))
    pending = SimpleNamespace(
        user=pending_user,
        signature_data=pending_signature_data,
        signed_at=django_timezone.now(),
    )
    rows = existing + [pending]
    signatures_pdf_bytes = _render_signatures_pdf_bytes(rows, document.title)

    document.file.open('rb')
    original_reader = PdfReader(document.file)
    writer = PdfWriter()

    for page in original_reader.pages:
        writer.add_page(page)

    signatures_reader = PdfReader(BytesIO(signatures_pdf_bytes))
    for page in signatures_reader.pages:
        writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output.read()


def rebuild_signed_pdf(document) -> None:
    """
    Genera y guarda el PDF firmado:
    - Base: PDF original cargado en document.file
    - Última(s) página(s): hoja de firmas acumulada
    Se regenera en cada firma para reflejar el estado actual.
    """
    if not document.file:
        raise ValueError('El documento no tiene archivo base.')
    if not document.file.name or not document.file.storage.exists(document.file.name):
        raise ValueError('No se encontró el archivo base del documento en el almacenamiento.')

    document.file.open('rb')
    original_reader = PdfReader(document.file)
    writer = PdfWriter()

    for page in original_reader.pages:
        writer.add_page(page)

    signatures_pdf_bytes = _build_signatures_page(document)
    signatures_reader = PdfReader(BytesIO(signatures_pdf_bytes))
    for page in signatures_reader.pages:
        writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    output.seek(0)

    signed_name = f'document_{document.id}_signed.pdf'
    document.signed_file.save(signed_name, ContentFile(output.read()), save=False)
    document.save(update_fields=['signed_file', 'updated_at'])
