from django.conf import settings
from django.db import transaction
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Consent
from apps.analytics.events import track
from apps.analytics.models import EventName

from .models import InvestorMandate
from .permissions import IsConfirmedInvestor, IsVerifiedInvestor, is_status_confirmed
from .serializers import ConfirmStatusSerializer, MandateOutSerializer, MandateSerializer

MANDATE_FIELDS = ("sectors", "stages", "regions", "business_models", "ticket_min", "ticket_max")


def snapshot(mandate: InvestorMandate) -> dict:
    """Comparable, JSON-safe view of a mandate (money as fixed 2-decimals strings)."""
    out = {}
    for f in MANDATE_FIELDS:
        v = getattr(mandate, f)
        out[f] = f"{v:.2f}" if f.startswith("ticket_") else list(v)
    return out


def build_state(user) -> dict:
    consent = (
        Consent.objects.filter(user=user, document_type=Consent.DocumentType.INVESTOR_STATUS)
        .order_by("accepted_at")
        .first()
    )
    mandate = InvestorMandate.objects.filter(user=user).first()
    return {
        "status_confirmed": consent is not None,
        "status_confirmed_at": consent.accepted_at if consent else None,
        "mandate": MandateOutSerializer(mandate).data if mandate else None,
    }


class InvestorStateView(APIView):
    """One call for the cabinet: is text C confirmed, and the saved mandate (or null)."""

    permission_classes = [IsVerifiedInvestor]

    def get(self, request):
        return Response(build_state(request.user))


class ConfirmStatusView(APIView):
    """Text C: "Ich handle als professioneller Investor ... und nicht als Verbraucher". Idempotent."""

    permission_classes = [IsVerifiedInvestor]

    def post(self, request):
        s = ConfirmStatusSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if not is_status_confirmed(request.user):
            Consent.objects.create(
                user=request.user,
                document_type=Consent.DocumentType.INVESTOR_STATUS,
                document_version=settings.LEGAL_DOCUMENT_VERSIONS["investor-status"],
            )
            track(EventName.STATUS_CONFIRMED, request.user)
        return Response(build_state(request.user))


class MandateView(APIView):
    """PUT = save the whole mandate. First save -> mandate_saved, later real changes -> mandate_changed."""

    permission_classes = [IsConfirmedInvestor]

    def put(self, request):
        s = MandateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data

        with transaction.atomic():
            mandate = InvestorMandate.objects.select_for_update().filter(user=request.user).first()
            created = mandate is None
            before = None if created else snapshot(mandate)
            if created:
                mandate = InvestorMandate(user=request.user)
            for f in MANDATE_FIELDS:
                setattr(mandate, f, data[f])
            mandate.save()
            after = snapshot(mandate)

        if created:
            track(EventName.MANDATE_SAVED, request.user, **after)
        elif before != after:
            changed = [f for f in MANDATE_FIELDS if before[f] != after[f]]
            # source "suggestion" is reserved for the criterion-suggestion feature (feedback loop, later)
            track(EventName.MANDATE_CHANGED, request.user, source="self", changed=changed, **after)
        return Response(MandateOutSerializer(mandate).data)
