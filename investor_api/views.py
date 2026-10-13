from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Этот импорт нужно согласовать с командой при интеграции моделей.
from .models import (
    Introduction,
    DeclineReason,
    CriterionSuggestion,
    PlatformParameter,
    Event,
)

from .serializers import (
    IntroductionDecisionSerializer,
    CriterionSuggestionDecisionSerializer,
)


def create_investor_event(
    request,
    event_name,
    entity_type,
    entity_id,
    properties=None,
):
    """Записывает событие для аналитики."""
    Event.objects.create(
        event_name=event_name,
        user_id=request.user.id,
        role="investor",
        entity_type=entity_type,
        entity_id=entity_id,
        properties=properties or {},
    )


class IntroductionDecisionView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, public_id):
        # Находим предложение для инвестора.
        introduction = (
            Introduction.objects
            .select_for_update()
            .filter(public_id=public_id)
            .first()
        )

        if introduction is None:
            return Response(
                {"detail": "Пропозицію не знайдено."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Проверяем, что это предложение именно данного инвестора.
        if introduction.investor_profile.user_id != request.user.id:
            return Response(
                {"detail": "Немає доступу до цієї пропозиції."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Решение по предложению можно принять только один раз.
        if introduction.status != Introduction.Status.SUGGESTED:
            return Response(
                {"detail": "Рішення щодо цієї пропозиції вже прийнято."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = IntroductionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        now = timezone.now()
        introduction.investor_message = data.get("investor_message", "")

        if data["interested"]:
            introduction.status = Introduction.Status.INTERESTED
            introduction.interested_at = now
            introduction.save()

            create_investor_event(
                request=request,
                event_name="interested",
                entity_type="introduction",
                entity_id=introduction.pk,
            )

            return Response({
                "status": introduction.status,
                "message": "Рішення «Цікаво» збережено.",
            })

        # Для ответа «Ні» получаем причину из справочника.
        reason_code = data["decline_reason_code"]

        try:
            reason = DeclineReason.objects.get(code=reason_code)
        except DeclineReason.DoesNotExist:
            return Response(
                {"decline_reason_code": "Невідома причина відмови."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        introduction.status = Introduction.Status.DECLINED
        introduction.declined_at = now
        introduction.declined_by = Introduction.DeclinedBy.INVESTOR
        introduction.decline_reason = reason
        introduction.save()

        create_investor_event(
            request=request,
            event_name="declined",
            entity_type="introduction",
            entity_id=introduction.pk,
            properties={"decline_reason_code": reason.code},
        )

        suggestion = self._check_criterion_suggestion(
            request=request,
            introduction=introduction,
            reason=reason,
        )

        response_data = {
            "status": introduction.status,
            "message": "Відмову збережено.",
            "criterion_suggestion": None,
        }

        if suggestion is not None:
            response_data["criterion_suggestion"] = {
                "id": suggestion.pk,
                "criterion": suggestion.criterion,
                "decline_count": suggestion.decline_count,
            }

        return Response(response_data)

    def _check_criterion_suggestion(
        self,
        request,
        introduction,
        reason,
    ):
        # Причина должна быть связана с конкретным критерием.
        criterion = reason.mandate_criterion

        if not criterion:
            return None

        # Порог берём из настроек платформы; по умолчанию — 3.
        parameter = PlatformParameter.objects.filter(
            key="decline_suggestion_threshold"
        ).first()

        try:
            threshold = int(parameter.value) if parameter else 3
        except (TypeError, ValueError):
            threshold = 3

        # Считаем отказы этого инвестора по данному критерию.
        decline_count = Introduction.objects.filter(
            investor_profile=introduction.investor_profile,
            status=Introduction.Status.DECLINED,
            declined_by=Introduction.DeclinedBy.INVESTOR,
            decline_reason__mandate_criterion=criterion,
        ).count()

        if decline_count < threshold:
            return None

        # Не показываем повторно уже активное предложение
        # по тому же критерию и версии мандата.
        active_suggestion = CriterionSuggestion.objects.filter(
            investor_profile=introduction.investor_profile,
            mandate=introduction.mandate,
            criterion=criterion,
            accepted_at__isnull=True,
            dismissed_at__isnull=True,
        ).exists()

        if active_suggestion:
            return None

        suggestion = CriterionSuggestion.objects.create(
            investor_profile=introduction.investor_profile,
            mandate=introduction.mandate,
            decline_reason=reason,
            criterion=criterion,
            decline_count=decline_count,
        )

        create_investor_event(
            request=request,
            event_name="criterion_suggestion_shown",
            entity_type="criterion_suggestion",
            entity_id=suggestion.pk,
            properties={
                "criterion": criterion,
                "decline_count": decline_count,
            },
        )

        return suggestion


class CriterionSuggestionDecisionView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        suggestion = (
            CriterionSuggestion.objects
            .select_for_update()
            .filter(pk=pk)
            .first()
        )

        if suggestion is None:
            return Response(
                {"detail": "Пропозицію зміни критерію не знайдено."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if suggestion.investor_profile.user_id != request.user.id:
            return Response(
                {"detail": "Немає доступу до цієї пропозиції."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            suggestion.accepted_at is not None
            or suggestion.dismissed_at is not None
        ):
            return Response(
                {"detail": "На цю пропозицію вже надано відповідь."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CriterionSuggestionDecisionSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        now = timezone.now()

        if serializer.validated_data["accepted"]:
            suggestion.accepted_at = now
            suggestion.save()

            create_investor_event(
                request=request,
                event_name="criterion_suggestion_accepted",
                entity_type="criterion_suggestion",
                entity_id=suggestion.pk,
                properties={"criterion": suggestion.criterion},
            )

            message = "Пропозицію прийнято."
        else:
            suggestion.dismissed_at = now
            suggestion.save()

            message = "Пропозицію відхилено."

        return Response({
            "id": suggestion.pk,
            "accepted_at": suggestion.accepted_at,
            "dismissed_at": suggestion.dismissed_at,
            "message": message,
        })

