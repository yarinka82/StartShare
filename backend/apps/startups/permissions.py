from rest_framework.permissions import BasePermission

from apps.accounts.models import UserRole


class IsVerifiedStartup(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == UserRole.STARTUP and u.is_email_verified)
