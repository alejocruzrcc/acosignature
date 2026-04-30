import os
import json

from django import forms
from django.contrib.auth import get_user_model
from django.db import models

from documents.models import Document
from documents.validators import validate_document_file

User = get_user_model()


class UserModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj: User) -> str:
        full = (obj.get_full_name() or '').strip()
        if full:
            return full
        return obj.get_username()


class DocumentCreateForm(forms.ModelForm):
    soy_firmante = forms.BooleanField(
        required=False,
        initial=True,
        label='Soy firmante',
    )
    ordered_signers = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = Document
        fields = ('title', 'category', 'description', 'file', 'requires_signature')

    def __init__(self, *args, **kwargs):
        uploader = kwargs.get('initial', {}).get('uploader') if kwargs.get('initial') else None
        super().__init__(*args, **kwargs)

        qs = User.objects.filter(is_active=True).order_by('last_name', 'first_name', 'username')
        self.available_signers = list(qs)
        self.uploader = uploader

    def clean_file(self):
        file = self.cleaned_data['file']
        validate_document_file(file)
        ext = os.path.splitext(file.name)[1].lower()
        content_type = (getattr(file, 'content_type', '') or '').lower()
        if ext != '.pdf' or (content_type and content_type not in {'application/pdf', 'application/x-pdf'}):
            raise forms.ValidationError('Solo se permiten archivos PDF.')
        return file

    def clean(self):
        cleaned_data = super().clean()
        raw_ordered_signers = (cleaned_data.get('ordered_signers') or '').strip()
        selected_ids = []
        if raw_ordered_signers:
            try:
                parsed = json.loads(raw_ordered_signers)
            except json.JSONDecodeError as exc:
                raise forms.ValidationError('No se pudo interpretar el orden de firmantes.') from exc
            if not isinstance(parsed, list):
                raise forms.ValidationError('El orden de firmantes debe ser una lista válida.')
            try:
                selected_ids = [int(value) for value in parsed]
            except (TypeError, ValueError) as exc:
                raise forms.ValidationError('El orden de firmantes contiene valores inválidos.') from exc

        if len(selected_ids) != len(set(selected_ids)):
            raise forms.ValidationError('No puedes repetir firmantes en la lista.')

        uploader = self.uploader
        soy_firmante = cleaned_data.get('soy_firmante', False)
        if uploader:
            if soy_firmante and uploader.id not in selected_ids:
                selected_ids.insert(0, uploader.id)
            if not soy_firmante:
                selected_ids = [user_id for user_id in selected_ids if user_id != uploader.id]

        allowed_ids = {u.id for u in self.available_signers}
        invalid_ids = [user_id for user_id in selected_ids if user_id not in allowed_ids]
        if invalid_ids:
            raise forms.ValidationError('Hay firmantes inválidos en el orden seleccionado.')

        user_map = {u.id: u for u in self.available_signers}
        users = [user_map[user_id] for user_id in selected_ids]

        if not users:
            raise forms.ValidationError('Debes definir al menos un firmante para el documento.')

        cleaned_data['firmantes'] = users
        return cleaned_data


class SignatureCaptureForm(forms.Form):
    ALLOWED_UPLOAD_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
    ALLOWED_UPLOAD_CONTENT_TYPES = {
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/webp',
        'image/gif',
        'image/bmp',
    }

    class SignatureMode(models.TextChoices):
        DRAW = 'draw', 'Dibujar firma'
        SAVED = 'saved', 'Usar firma guardada'
        UPLOAD = 'upload', 'Subir imagen de firma'

    signature_mode = forms.ChoiceField(choices=SignatureMode.choices)
    signature_data = forms.CharField(required=False)
    signature_upload = forms.ImageField(required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get('signature_mode')
        signature_data = cleaned_data.get('signature_data')
        signature_upload = cleaned_data.get('signature_upload')

        if mode == self.SignatureMode.DRAW and not signature_data:
            self.add_error('signature_data', 'Dibuja la firma antes de continuar.')

        if mode == self.SignatureMode.SAVED:
            has_saved = bool(self.user and self.user.signature_image)
            if not has_saved:
                self.add_error('signature_mode', 'No tienes una firma guardada. Sube una imagen o dibuja tu firma.')

        if mode == self.SignatureMode.UPLOAD and not signature_upload:
            self.add_error('signature_upload', 'Selecciona una imagen de firma para continuar.')
        elif mode == self.SignatureMode.UPLOAD and signature_upload:
            ext = os.path.splitext((signature_upload.name or '').lower())[1]
            content_type = (getattr(signature_upload, 'content_type', '') or '').lower()
            if ext not in self.ALLOWED_UPLOAD_EXTENSIONS:
                self.add_error(
                    'signature_upload',
                    'Formato no permitido. Usa JPG, JPEG, PNG, WEBP, GIF o BMP.',
                )
            elif content_type and content_type not in self.ALLOWED_UPLOAD_CONTENT_TYPES:
                self.add_error(
                    'signature_upload',
                    'Tipo de archivo no válido. Usa JPG, JPEG, PNG, WEBP, GIF o BMP.',
                )

        return cleaned_data


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'email',
            'phone',
            'document_number',
            'cargo',
            'signature_image',
        )


class RejectionReasonForm(forms.Form):
    reason = forms.CharField(
        label='Razón de rechazo',
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Describe el motivo del rechazo...'}),
    )
