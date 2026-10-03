from rest_framework.permissions import BasePermission

from apps.accounts.models import Consent, Role


def is_status_confirmed(user) -> bool:
    return Consent.objects.filter(user=user, document_type=Consent.DocumentType.INVESTOR_STATUS).exists()


class IsVerifiedInvestor(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == Role.INVESTOR and u.is_email_verified)


class IsConfirmedInvestor(IsVerifiedInvestor):
    """Text C must be confirmed before anything else in the investor cabinet. Enforced on the server."""

    message = "status_not_confirmed"  # DRF puts this into the 403 body as "detail"

    def has_permission(self, request, view):
        return super().has_permission(request, view) and is_status_confirmed(request.user)
