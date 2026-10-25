from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db import transaction

from apps.accounts.models import LegalDocument, LegalDocumentCode, UserConsent, UserConsentContext
from apps.investors.models import Introduction
from apps.investors.services import intros
from apps.investors.tasks import send_intro

import logging

logger = logging.getLogger(__name__)


class StartupIntrosListView(APIView):
    """
    I3: GET /api/startups/intros/
    Список вхідних запитів від інвесторів для кабінету стартапу.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = getattr(request.user, "startup_profile", getattr(request.user, "startupprofile", None))
        if not profile:
            return Response([])

        now = timezone.now()

        # Знаходимо всі активні запити зі статусом INTERESTED
        intros_qs = (
            Introduction.objects.filter(
                startup_profile=profile,
                status=Introduction.Status.INTERESTED,
            )
            .select_related("investor_profile", "investor_profile__user")
            .order_by("-interested_at")
        )

        data = []
        for intro in intros_qs:
            inv = intro.investor_profile

            inv_type_display = "Professional Investor"
            if hasattr(inv, "investor_type") and inv.investor_type:
                inv_type_display = (
                    getattr(inv.investor_type, "name", None)
                    or getattr(inv.investor_type, "name_de", None)
                    or getattr(inv.investor_type, "code", None)
                    or str(inv.investor_type)
                )

            can_respond = bool(intro.request_expires_at and intro.request_expires_at > now)

            data.append({
                "id": str(intro.public_id),
                "investor_name": getattr(inv, "organization_name", "Investor"),
                "investor_type": inv_type_display,
                "message": intro.investor_message or "",
                "status": intro.status,
                "interested_at": intro.interested_at.isoformat() if intro.interested_at else None,
                "expires_at": intro.request_expires_at.isoformat() if intro.request_expires_at else None,
                "can_respond": can_respond,
            })

        return Response(data)



class StartupIntroRespondView(APIView):
    """
    I4: POST /api/startups/intros/<str:public_id>/respond/
    Тіло: {"action": "freigabe"} або {"action": "nein"}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, public_id):
        action = request.data.get("action")
        if action not in ("freigabe", "nein"):
            return Response(
                {"detail": "Дія повинна бути 'freigabe' або 'nein'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = getattr(request.user, "startup_profile", getattr(request.user, "startupprofile", None))
        if not profile:
            return Response({"detail": "Startup profile not found."}, status=status.HTTP_404_NOT_FOUND)

        # Знаходимо інтро за public_id або pk
        intro = Introduction.objects.filter(startup_profile=profile)
        if str(public_id).isdigit():
            intro = intro.filter(id=int(public_id)).first()
        else:
            intro = intro.filter(public_id=public_id).first()

        if not intro:
            return Response({"detail": "Запит не знайдено."}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()

        # 1. Перевірка терміну за ТЗ I4: після expires_at повертаємо 409 Conflict
        if intro.request_expires_at and intro.request_expires_at <= now:
            try:
                updated_intro = intros.accept(intro.id, user=request.user)
            except intros.InvalidTransition:
                return Response({"detail": "intro_not_respondable"}, status=status.HTTP_409_CONFLICT)

        # 2. Обробка дій через сервіс кінцевого автомата (I1)
        if action == "freigabe":
            with transaction.atomic():
                # Фіксуємо доказ згоди за Текстом D у журналі згод (ТЗ I4)
                doc_d = (
                    LegalDocument.objects.filter(code=LegalDocumentCode.D, language="de")
                    .order_by("-version").first()
                )
                if doc_d is None:
                    logger.error("Legal text D is not seeded")
                    return Response({"detail": "legal_text_unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                UserConsent.objects.create(
                    user=request.user,
                    legal_document=doc_d,
                    context=getattr(UserConsentContext, "REGISTRATION", "intro_freigabe"),
                )

                # Переводимо ТІЛЬКИ в ACCEPTED (не в INTRODUCED!) через State Machine
                updated_intro = intros.accept(intro.id, user=request.user)

                # Ставимо Celery-задачу відправки листів з Текстом E (I5)
                transaction.on_commit(lambda: send_intro.delay(updated_intro.id), robust=True)

        elif action == "nein":
            # Відхилення без вимоги причини (ТЗ I4)
            intros.decline_by_startup(intro.id, user=request.user)

        return Response({"status": "ok", "decision": action}, status=status.HTTP_200_OK)