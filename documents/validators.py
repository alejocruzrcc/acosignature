import os

from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png'}
MAX_FILE_SIZE = 10 * 1024 * 1024


def validate_document_file(uploaded_file):
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError('Tipo de archivo no permitido.')
    if uploaded_file.size > MAX_FILE_SIZE:
        raise ValidationError('Archivo supera 10MB.')
