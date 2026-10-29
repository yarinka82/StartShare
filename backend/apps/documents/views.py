import os
import re
from datetime import timedelta

from django.db import transaction
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView


from ..analytics.services import can_replace_deck, start_teaser_job
from ..documents.models import TeaserStatus, PitchDeckDeletionReason, Teaser, PitchDeckProcessingState, PitchDeck
from ..documents.serializers import DeckSerializer, DeckUploadSerializer
from ..startups.views import get_profile



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
