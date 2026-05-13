from django.contrib import admin

from .models import Signature


@admin.register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    list_display = ('id', 'document', 'user', 'signed_at', 'is_valid')
    list_filter = ('is_valid', 'signed_at')
    readonly_fields = ('signed_at', 'ip_address')
    search_fields = ('signer_note',)
