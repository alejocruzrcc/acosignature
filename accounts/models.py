from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        REVIEWER = 'reviewer', 'Reviewer'
        CLIENT = 'client', 'Client'

    document_number = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    cargo = models.CharField(max_length=120, blank=True)
    signature_image = models.ImageField(upload_to='user_signatures/', blank=True, null=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.CLIENT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
