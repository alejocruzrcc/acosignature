from rest_framework.permissions import BasePermission

from .models import User


class IsReviewerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in {User.Roles.ADMIN, User.Roles.REVIEWER})
