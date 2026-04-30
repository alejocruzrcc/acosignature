from __future__ import annotations

import base64
import re
from io import BytesIO
from typing import Tuple

from django.core.files.base import ContentFile
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


def _build_signatures_page(document) -> bytes:
    """
    Construye una o más páginas de firmas con:
    - imagen de firma
    - nombre completo (o username)
    - número de documento del firmante
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    margin_x = 48
    margin_y = 42

    signatures = list(document.signatures.select_related('user').order_by('signed_at', 'id'))

    c.setTitle(f'Firmas - {document.title}')
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
