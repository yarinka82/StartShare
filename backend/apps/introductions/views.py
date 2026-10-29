from django.core.exceptions import ValidationError
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import InvalidTransition
from .models import Introduction, IntroductionService, StartupIntroDecisionLog
from .serializers import IntroductionSerializer


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y"}:
            return True
        if lowered in {"0", "false", "no", "n"}:
            return False
    return bool(value)


def _startup_response_payload(introduction, detail=None, *, can_respond=None):
    payload = {"id": introduction.pk, "status": introduction.status}
    if detail is not None:
        payload["detail"] = detail
    if can_respond is not None:
        payload["can_respond"] = can_respond
    return payload


# I2: investor action endpoint for "Interested".
# It validates the confirmation flag and creates the state transition SUGGESTED -> INTERESTED.
class IntroductionInterestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        introduction = Introduction.objects.get(pk=kwargs["pk"])
        try:
            accepted = _coerce_bool(request.data.get("notification_accepted"))
            if not accepted:
                return Response({"detail": "Investor notification confirmation is required."}, status=status.HTTP_400_BAD_REQUEST)
            intro = IntroductionService.interest(
                introduction,
                request.data.get("message"),
                notification_accepted=accepted,
            )
            return Response({"id": intro.pk, "status": intro.status}, status=status.HTTP_200_OK)
        except (ValidationError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except InvalidTransition as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)


# I2: investor action endpoint for "No" (decline).
# It records the selected decline reason and closes the flow without exposing private contact data.
class IntroductionDeclineView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        introduction = Introduction.objects.get(pk=kwargs["pk"])
        try:
            intro = IntroductionService.decline_by_investor(introduction, request.data.get("reason"))
            return Response({"id": intro.pk, "status": intro.status, "reason": intro.decline_reason}, status=status.HTTP_200_OK)
        except (ValidationError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except InvalidTransition as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)


# I4: startup approval endpoint. This is the Freigabe decision and is restricted to the profile owner.
class IntroductionAcceptView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        introduction = Introduction.objects.select_related("startup", "investor").get(pk=kwargs["pk"])
        if getattr(introduction.startup, "owner", None) != request.user:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        if not introduction.can_respond:
            return Response(_startup_response_payload(introduction, "Request expired or not active.", can_respond=False), status=status.HTTP_409_CONFLICT)
        try:
            intro = IntroductionService.accept(
                introduction,
                user=request.user,
                text_version="intro-request-v1",
            )
            return Response({"id": intro.pk, "status": intro.status, "can_respond": True}, status=status.HTTP_200_OK)
        except InvalidTransition as exc:
            return Response(_startup_response_payload(introduction, str(exc), can_respond=False), status=status.HTTP_409_CONFLICT)


# I4: startup rejection endpoint. Nein closes the flow and does not disclose contact details.
class IntroductionStartupDeclineView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        introduction = Introduction.objects.select_related("startup", "investor").get(pk=kwargs["pk"])
        if getattr(introduction.startup, "owner", None) != request.user:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        if not introduction.can_respond:
            return Response(_startup_response_payload(introduction, "Request expired or not active.", can_respond=False), status=status.HTTP_409_CONFLICT)
        try:
            intro = IntroductionService.decline_by_startup(introduction, user=request.user, text_version="intro-request-v1")
            return Response({"id": intro.pk, "status": intro.status, "can_respond": False}, status=status.HTTP_200_OK)
        except InvalidTransition as exc:
            return Response(_startup_response_payload(introduction, str(exc), can_respond=False), status=status.HTTP_409_CONFLICT)


# I4: API aliases matching the explicit business terms from the task description.
class IntroductionFreigabeView(IntroductionAcceptView):
    pass


class IntroductionNeinView(IntroductionStartupDeclineView):
    pass


# I3: startup request list and detail endpoints.
# These endpoints show pending intro requests to the startup, without exposing investor contacts in the email body.
class StartupIntroductionRequestListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        startup_id = request.query_params.get("startup_id")
        owned_startups = request.user.startup_profiles.all()
        if not owned_startups.exists():
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        queryset = Introduction.objects.filter(startup__owner=request.user)
        if startup_id:
            queryset = queryset.filter(startup_id=startup_id, startup__owner=request.user)
        serializer = IntroductionSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StartupIntroductionRequestDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        introduction = Introduction.objects.get(pk=kwargs["pk"])
        if getattr(introduction.startup, "owner", None) != request.user:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        serializer = IntroductionSerializer(introduction)
        return Response(serializer.data, status=status.HTTP_200_OK)
