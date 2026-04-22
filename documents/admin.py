from django.contrib import admin

from .models import Document, DocumentSignatory


class DocumentSignatoryInline(admin.TabularInline):
    model = DocumentSignatory
    extra = 0


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'uploaded_by', 'status', 'requires_signature', 'created_at')
    list_filter = ('status', 'requires_signature')
    search_fields = ('title', 'uploaded_by__username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = (DocumentSignatoryInline,)


@admin.register(DocumentSignatory)
class DocumentSignatoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'document', 'user', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('document__title', 'user__username')
