from django import forms
from django.contrib.auth import get_user_model

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
    signature_data = forms.CharField()
