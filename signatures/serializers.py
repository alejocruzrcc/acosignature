from rest_framework import serializers

from documents.models import Document
from workflows.services import WorkflowService

from .models import Signature


class SignatureSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    signer_note = serializers.CharField(required=False, allow_blank=True, max_length=4000)

    class Meta:
        model = Signature
        fields = ('id', 'document', 'user', 'signed_at', 'ip_address', 'signature_data', 'signer_note', 'is_valid')
        read_only_fields = ('id', 'user', 'signed_at', 'ip_address', 'is_valid')

    def validate_document(self, value):
        if value.status in {Document.Status.APPROVED, Document.Status.REJECTED}:
            raise serializers.ValidationError('Documento cerrado, no se puede firmar.')
        return value

    def create(self, validated_data):
        request = self.context['request']
        client_ip = self._get_ip(request)
        document = validated_data['document']
        note = (validated_data.get('signer_note') or '').strip()
        signature, _created = Signature.objects.update_or_create(
            document=document,
            user=request.user,
            defaults={
                'signature_data': validated_data['signature_data'],
                'signer_note': note,
                'ip_address': client_ip,
                'is_valid': True,
            },
        )
        try:
            WorkflowService.sign_document(signature.document, request.user, ip_address=client_ip)
        except ValueError as exc:
            raise serializers.ValidationError({'document': str(exc)}) from exc
        return signature

    @staticmethod
    def _get_ip(request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
