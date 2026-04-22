from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_verified', 'is_staff')
    list_filter = ('role', 'is_verified', 'is_staff')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = UserAdmin.fieldsets + (
        ('Extra', {'fields': ('document_number', 'phone', 'role', 'is_verified', 'created_at', 'updated_at')}),
    )
