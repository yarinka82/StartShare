from rest_framework.permissions import BasePermission

from apps.accounts.models import Role


class IsVerifiedStartup(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == Role.STARTUP and u.is_email_verified)
