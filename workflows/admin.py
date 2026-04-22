from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'action', 'actor', 'document', 'ip_address', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('actor__username', 'document__title', 'ip_address')
    readonly_fields = ('created_at',)
