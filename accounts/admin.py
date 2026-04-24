from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'cargo', 'role', 'is_staff')
    list_filter = ('role', 'is_staff')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = UserAdmin.fieldsets + (
        (
            'Extra',
            {
                'fields': (
                    'document_number',
                    'phone',
                    'cargo',
                    'signature_image',
                    'role',
                    'created_at',
                    'updated_at',
                )
            },
        ),
    )
