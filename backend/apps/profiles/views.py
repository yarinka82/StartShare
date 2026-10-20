import os
import re
from datetime import timedelta

from django.db import transaction
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import Sector, Stage, BusinessModel, Country, Region
from .permissions import IsVerifiedStartup

from ..analytics.services import can_replace_deck, start_teaser_job
from ..documents.models import TeaserStatus, PitchDeckDeletionReason, Teaser, PitchDeckProcessingState, PitchDeck

from ..documents.serializers import DeckSerializer, DeckUploadSerializer
from ..startups.models import StartupProfile
from ..startups.serializers import StartupProfileSerializer

GROWTH_PERIODS = [
    {"code": "mom", "name": "MoM (Month over month)"},
    {"code": "qoq", "name": "QoQ (Quarter over quarter)"},
    {"code": "yoy", "name": "YoY (Year over year)"},
]

def get_profile(user):
    return StartupProfile.objects.get_or_create(user=user)[0]


def serialize_reference(queryset, lang: str = "de"):
    """Допоміжна функція: перетворює QuerySet ReferenceModel у список {code, name, is_other}."""
    name_field = "name_en" if lang.startswith("en") else "name_de"
    result = []
    for item in queryset:
        data = {
            "code": item.code,
            "name": getattr(item, name_field, item.name_de),
        }
        # Якщо в моделі є поле is_other (для Sector та BusinessModel)
        if hasattr(item, "is_other"):
            data["is_other"] = item.is_other
        result.append(data)
    return result


class DictionariesView(APIView):
    """Повертає всі довідники для стартапів та інвесторів в одному запиті."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            "sectors": [
                {"code": s.code, "name": s.name_de}
                for s in Sector.objects.filter(is_active=True)
            ],
            "stages": [
                {"code": s.code, "name": s.name_de}
                for s in Stage.objects.filter(is_active=True)
            ],
            "business_models": [
                {"code": b.code, "name": b.name_de}
                for b in BusinessModel.objects.filter(is_active=True)
            ],
            "regions": [
                {"code": r.code, "name": r.name_de}
                for r in Region.objects.filter(is_active=True)
            ],
            "countries": [
                {"code": c.code, "name": c.name_de}
                for c in Country.objects.filter(is_active=True)
            ],
            "growth_periods": GROWTH_PERIODS,
        })



class ProfileView(RetrieveUpdateAPIView):
    """GET / PUT / PATCH: PUT is also partial, so the form can autosave a draft."""

    permission_classes = [IsVerifiedStartup]
    serializer_class = StartupProfileSerializer

    def get_object(self):
        return get_profile(self.request.user)

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)



class DeckView(APIView):
    """Эндпоинт загрузки, получения и удаления Pitch Deck (/api/profile/deck/)."""

    # permission_classes = [IsVerifiedStartup] # ваш класс прав
    parser_classes = [MultiPartParser]

    def get_current_deck(self, profile) -> "PitchDeck | None":
        """Возвращает текущий активный (неудалённый) дек стартапа."""
        return profile.pitch_decks.filter(deleted_at__isnull=True).order_by("-uploaded_at").first()

    def get(self, request):
        profile = get_profile(request.user)
        deck = self.get_current_deck(profile)
        if deck is None or not deck.file:
            return Response({"detail": "no_deck"}, status=status.HTTP_404_NOT_FOUND)
        return Response(DeckSerializer(deck).data)

    def post(self, request):
        s = DeckUploadSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        upload = s.validated_data["file"]
        profile = get_profile(request.user)

        # 1. Проверяем, разрешена ли замена дека (запрещена только в статусе LIVE)
        if not can_replace_deck(profile):
            return Response({"detail": "teaser_approved"}, status=status.HTTP_409_CONFLICT)

        # 2. Очищаем имя файла от небезопасных управляющих символов
        clean_name = re.sub(r"[\x00-\x1f]", "", os.path.basename(upload.name))[:255]
        now = timezone.now()

        with transaction.atomic():
            # Создаём новую запись PitchDeck
            pitch_deck = PitchDeck.objects.create(
                startup_profile=profile,
                file=upload,
                original_name=clean_name,
                file_size_bytes=upload.size,
                mime_type="application/pdf",
                uploaded_at=now,
                delete_after=now + timedelta(hours=24),  # Политика автоудаления через 24 часа
                processing_state=PitchDeckProcessingState.QUEUED,
            )
            # Архивация старых деков и запуск Celery-задачи
            start_teaser_job(pitch_deck, request.user)

        return Response(DeckSerializer(pitch_deck).data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        profile = get_profile(request.user)
        deck = self.get_current_deck(profile)

        if deck is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not can_replace_deck(profile):
            return Response({"detail": "teaser_approved"}, status=status.HTTP_409_CONFLICT)

        with transaction.atomic():
            # Мягкое удаление (Soft Delete) с фиксацией причины в аудите
            deck.deleted_at = timezone.now()
            deck.deletion_reason = PitchDeckDeletionReason.USER_REQUEST
            if deck.file:
                deck.file.delete(save=False)
            deck.storage_key = None
            deck.save(update_fields=["deleted_at", "deletion_reason", "storage_key"])

            # Текущий тизер переводим в статус заменённого (SUPERSEDED)
            Teaser.objects.filter(
                startup_profile=profile,
                is_current=True,
            ).update(is_current=False, status=TeaserStatus.SUPERSEDED)

        return Response(status=status.HTTP_204_NO_CONTENT)



class DeckDownloadView(APIView):
    """GET /api/profile/deck/download/ — скачивание своего PDF-файла владельцем."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = getattr(request.user, "startup_profile", None)
        if not profile:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Ищем активный неудалённый дек стартапа
        pitch_deck = (
            profile.pitch_decks.filter(deleted_at__isnull=True)
            .order_by("-uploaded_at")
            .first()
        )

        if pitch_deck is None or not pitch_deck.file:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Отдаём стриминг PDF-файла
        try:
            file_handle = pitch_deck.file.open("rb")
            response = FileResponse(file_handle, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{pitch_deck.original_name}"'
            return response
        except FileNotFoundError:
            return Response(status=status.HTTP_404_NOT_FOUND)
