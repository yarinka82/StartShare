from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.models import Event, EventName
from apps.investors.models import Introduction
from apps.investors.services.emails import send_intro_completed_emails



class StartupIntrosListView(APIView):
    """
    GET /api/startups/intros/
    Повертає список вхідних запитів від інвесторів зі статусом INTERESTED (Текст D).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = getattr(request.user, "startup_profile", getattr(request.user, "startupprofile", None))
        if not profile:
            return Response([])

        now = timezone.now()

        # Знаходимо всі активні запити на інтро, які ще не прострочені
        intros = (
            Introduction.objects.filter(
                startup_profile=profile,
                status=Introduction.Status.INTERESTED,
            )
            .filter(request_expires_at__gt=now)
            .select_related("investor_profile", "investor_profile__user")
            .order_by("-interested_at")
        )

        data = []
        for intro in intros:
            inv = intro.investor_profile
            data.append({
                "id": str(intro.public_id),
                "investor_name": inv.organization_name,
                "investor_type": (
                    inv.investor_type.code
                    if hasattr(inv, "investor_type") and inv.investor_type
                    else "Professional Investor"
                ),
                "message": intro.investor_message or "",
                "interested_at": intro.interested_at.isoformat() if intro.interested_at else None,
                "expires_at": intro.request_expires_at.isoformat() if intro.request_expires_at else None,
            })
        return Response(data)



class StartupIntroRespondView(APIView):
    """
    POST /api/startups/intros/<str:public_id>/respond/
    Рішення стартапу щодо відкриття контактів:
    Тіло: {"action": "freigabe"} або {"action": "nein"}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, public_id):
        action = request.data.get("action")  # "freigabe" або "nein"
        if action not in ("freigabe", "nein"):
            return Response(
                {"detail": "Дія повинна бути 'freigabe' або 'nein'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = getattr(request.user, "startup_profile", getattr(request.user, "startupprofile", None))
        if not profile:
            return Response({"detail": "Startup profile not found."}, status=status.HTTP_404_NOT_FOUND)

        # Знаходимо запит інтро (підтримуємо як UUID public_id, так і pk)
        intro = Introduction.objects.filter(
            startup_profile=profile,
            status=Introduction.Status.INTERESTED,
        )
        if str(public_id).isdigit():
            intro = intro.filter(id=int(public_id)).first()
        else:
            intro = intro.filter(public_id=public_id).first()

        if not intro:
            return Response(
                {"detail": "Запит не знайдено, або його термін дії вже закінчився."},
                status=status.HTTP_404_NOT_FOUND,
            )

        now = timezone.now()

        with transaction.atomic():
            intro.startup_responded_at = now

            if action == "freigabe":
                # СТАРТАП ДАВ ЗГОДУ НА ВІДКРИТТЯ КОНТАКТІВ
                intro.status = Introduction.Status.INTRODUCED
                intro.accepted_at = now
                intro.introduced_at = now
                intro.save(update_fields=["status", "startup_responded_at", "accepted_at", "introduced_at"])

                # Надсилаємо обом сторонам контакти та Текст E (після фіксації транзакції)
                transaction.on_commit(lambda: send_intro_completed_emails(intro))

                try:
                    Event.objects.create(name=EventName.INTRODUCED, user=request.user)
                except Exception:
                    pass

            elif action == "nein":
                # Стартап відхилив запит на інтро
                intro.status = Introduction.Status.DECLINED
                intro.declined_at = now
                intro.declined_by = getattr(Introduction.DeclinedBy, "STARTUP", "startup")
                intro.save(update_fields=["status", "startup_responded_at", "declined_at", "declined_by"])

        return Response({"status": "ok", "decision": action}, status=status.HTTP_200_OK)