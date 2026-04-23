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
    firmantes = UserModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=True,
        widget=forms.SelectMultiple(
            attrs={
                'class': 'js-select2-users',
                'data-placeholder': 'Buscar y seleccionar firmantes…',
            }
        ),
    )

    class Meta:
        model = Document
        fields = ('title', 'description', 'file', 'requires_signature')

    def __init__(self, *args, **kwargs):
        uploader = kwargs.get('initial', {}).get('uploader') if kwargs.get('initial') else None
        super().__init__(*args, **kwargs)

        qs = User.objects.filter(is_active=True).order_by('last_name', 'first_name', 'username')
        if uploader:
            qs = qs.exclude(pk=uploader.pk)
        self.fields['firmantes'].queryset = qs

    def clean_file(self):
        file = self.cleaned_data['file']
        validate_document_file(file)
        return file

    def clean_firmantes(self):
        users = self.cleaned_data['firmantes']
        uploader = self.initial.get('uploader')
        if uploader and any(u.id == uploader.id for u in users):
            raise forms.ValidationError('No puedes incluirte a ti mismo como firmante.')
        if not users:
            raise forms.ValidationError('Selecciona al menos un firmante.')
        return users


class SignatureCaptureForm(forms.Form):
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
