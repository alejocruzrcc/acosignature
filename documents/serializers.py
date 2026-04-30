from rest_framework import serializers

from .models import Document
from .validators import validate_document_file


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Document
        fields = (
            'id', 'title', 'category', 'description', 'file', 'uploaded_by', 'status',
            'requires_signature', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'uploaded_by', 'status', 'created_at', 'updated_at')

    def validate_file(self, value):
        validate_document_file(value)
        return value
