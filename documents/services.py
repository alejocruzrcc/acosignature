from __future__ import annotations

import base64
import re
import textwrap
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


def _note_rows_from_document(
    document,
    pending_user=None,
    pending_note: str | None = None,
) -> List[Any]:
    rows: List[Any] = []
    for sig in document.signatures.select_related('user').order_by('signed_at', 'id'):
        t = (getattr(sig, 'signer_note', None) or '').strip()
        if t:
            rows.append(SimpleNamespace(user=sig.user, text=t, signed_at=sig.signed_at))
    if pending_user and pending_note and str(pending_note).strip():
        rows.append(
            SimpleNamespace(
                user=pending_user,
                text=str(pending_note).strip(),
                signed_at=django_timezone.now(),
            )
        )
    return rows


def _wrap_note_lines(text: str, width: int) -> List[str]:
    lines: List[str] = []
    for para in (text or '').replace('\r\n', '\n').split('\n'):
        stripped = para.strip()
        if not stripped:
            lines.append('')
            continue
        wrapped = textwrap.wrap(stripped, width=width) or ['']
        lines.extend(wrapped)
    return lines


def _render_notes_pdf_bytes(note_rows: List[Any], document_title: str) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    _width, height = A4
    margin_x = 48
    margin_y = 42
    wrap_chars = 88

    y = height - margin_y
    c.setTitle(f'Notas - {document_title}')
    c.setFont('Helvetica-Bold', 14)
    c.drawString(margin_x, y, 'Notas de firmantes')
    y -= 20
    c.setFont('Helvetica', 9)
    title_line = (document_title or '')[:140]
    c.drawString(margin_x, y, title_line)
    y -= 22

    for item in note_rows:
        user = item.user
        full_name = (user.get_full_name() or user.username).strip()
        header = f'{full_name} · {item.signed_at.strftime("%Y-%m-%d %H:%M UTC")}'
        c.setFont('Helvetica-Bold', 11)
        if y < margin_y + 100:
            c.showPage()
            y = height - margin_y
        c.drawString(margin_x, y, header)
        y -= 16
        c.setFont('Helvetica', 10)
        for line in _wrap_note_lines(item.text, wrap_chars):
            if y < margin_y + 16:
                c.showPage()
                y = height - margin_y
                c.setFont('Helvetica', 10)
            c.drawString(margin_x, y, line or ' ')
            y -= 14
        y -= 12

    c.save()
    return buf.getvalue()


def _merge_document_notes_signatures_pdf(
    document,
    signatures_pdf_bytes: bytes,
    note_rows: List[Any],
) -> bytes:
    if not document.file:
        raise ValueError('El documento no tiene archivo base.')
    if not document.file.name or not document.file.storage.exists(document.file.name):
        raise ValueError('No se encontró el archivo base del documento en el almacenamiento.')

    document.file.open('rb')
    original_reader = PdfReader(document.file)
    writer = PdfWriter()

    for page in original_reader.pages:
        writer.add_page(page)

    if note_rows:
        notes_pdf_bytes = _render_notes_pdf_bytes(note_rows, document.title)
        notes_reader = PdfReader(BytesIO(notes_pdf_bytes))
        for page in notes_reader.pages:
            writer.add_page(page)

    signatures_reader = PdfReader(BytesIO(signatures_pdf_bytes))
    for page in signatures_reader.pages:
        writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output.read()


def _build_signatures_page(document) -> bytes:
    """
    Construye una o más páginas de firmas con las firmas ya guardadas en BD.
    """
    signatures = list(document.signatures.select_related('user').order_by('signed_at', 'id'))
    return _render_signatures_pdf_bytes(signatures, document.title)


def build_signed_pdf_preview_bytes(
    document,
    pending_user,
    pending_signature_data: str,
    *,
    pending_signer_note: str = '',
) -> bytes:
    """
    PDF en memoria: documento original + notas de firmantes + hoja de firmas,
    incluyendo la firma (y nota) pendientes sin persistir cambios.
    """
    existing = list(document.signatures.select_related('user').order_by('signed_at', 'id'))
    pending = SimpleNamespace(
        user=pending_user,
        signature_data=pending_signature_data,
        signed_at=django_timezone.now(),
    )
    sig_rows = existing + [pending]
    signatures_pdf_bytes = _render_signatures_pdf_bytes(sig_rows, document.title)
    note_rows = _note_rows_from_document(document, pending_user, pending_signer_note)
    return _merge_document_notes_signatures_pdf(document, signatures_pdf_bytes, note_rows)


def rebuild_signed_pdf(document) -> None:
    """
    Genera y guarda el PDF firmado:
    - Base: PDF original cargado en document.file
    - Sección de notas (si hay notas registradas)
    - Última(s) página(s): hoja de firmas acumulada
    Se regenera en cada firma para reflejar el estado actual.
    """
    signatures_pdf_bytes = _build_signatures_page(document)
    note_rows = _note_rows_from_document(document)
    raw = _merge_document_notes_signatures_pdf(document, signatures_pdf_bytes, note_rows)

    signed_name = f'document_{document.id}_signed.pdf'
    document.signed_file.save(signed_name, ContentFile(raw), save=False)
    document.save(update_fields=['signed_file', 'updated_at'])
