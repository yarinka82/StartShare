
from rest_framework.permissions import BasePermission
from apps.accounts.models import UserConsent, UserRole


def is_status_confirmed(user) -> bool:
    """Перевіряє, чи підтвердив інвестор статус B2B."""
    if not user or not user.is_authenticated:
        return False
    return UserConsent.objects.filter(
        user=user,
        context=UserConsent.Context.INVESTOR_STATUS
    ).exists()


def build_state(user) -> dict:
    consent = (
        UserConsent.objects.filter(
            user=user,
            context=UserConsent.Context.INVESTOR_STATUS
        )
        .order_by("-accepted_at")
        .first()
    )
    from .models import InvestorMandate
    from .serializers import MandateOutSerializer

    mandate = InvestorMandate.objects.filter(user=user).first()
    return {
        "status_confirmed": consent is not None,
        "status_confirmed_at": consent.accepted_at if consent else None,
        "mandate": MandateOutSerializer(mandate).data if mandate else None,
    }


class IsVerifiedInvestor(BasePermission):
    """Користувач має бути автентифікованим інвестором із підтвердженим email."""
    message = "investor_required"

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == UserRole.INVESTOR
            and getattr(request.user, "is_email_verified", True)
        )


class IsConfirmedInvestor(IsVerifiedInvestor):
    """Text C must be confirmed before anything else in the investor cabinet. Enforced on the server."""
    message = "status_not_confirmed"  # DRF повертає це в тілі 403 як "detail"

    def has_permission(self, request, view):
        return super().has_permission(request, view) and is_status_confirmed(request.user)
