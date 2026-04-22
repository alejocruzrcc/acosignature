from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'uploaded_by', 'status', 'requires_signature', 'created_at')
    list_filter = ('status', 'requires_signature')
    search_fields = ('title', 'uploaded_by__username')
    readonly_fields = ('created_at', 'updated_at')
