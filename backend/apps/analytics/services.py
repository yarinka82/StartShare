"""Точки входа для работы с презентациями (PitchDeck) и тизерами."""

import logging
from django.db import transaction
from django.utils import timezone

from apps.analytics.events import track
from apps.analytics.models import EventName
from apps.documents.models import (
    PitchDeck,
    PitchDeckDeletionReason,
    PitchDeckProcessingState,
    Teaser,
    TeaserStatus,
)

logger = logging.getLogger(__name__)


def can_replace_deck(profile) -> bool:
    """
    Замена и удаление дека блокируются ТОЛЬКО если профиль активен (LIVE).
    Если профиль на паузе (PAUSED) или в черновике (DRAFT) — замена разрешена.
    """
    # Если в модели есть Enum статусов — лучше использовать его, иначе строковый фоллбек
    live_status = getattr(getattr(profile, "Status", None), "LIVE", "LIVE")
    return getattr(profile, "status", None) != live_status


def start_teaser_job(pitch_deck: PitchDeck, user) -> PitchDeck:
    from apps.documents.tasks import process_deck

    profile = pitch_deck.startup_profile

    # Помечаем старые деки и удаляем их файлы
    previous_decks = PitchDeck.objects.filter(
        startup_profile=profile,
        deleted_at__isnull=True,
    ).exclude(pk=pitch_deck.pk)

    now = timezone.now()
    for old_deck in previous_decks:
        old_deck.deleted_at = now
        old_deck.deletion_reason = PitchDeckDeletionReason.REPLACED
        if old_deck.file:
            old_deck.file.delete(save=False)  # Удаляем сразу для прохождения тестов
        old_deck.storage_key = None
        old_deck.save(update_fields=["deleted_at", "deletion_reason", "storage_key"])

    # Старые тизеры переводятся в SUPERSEDED
    Teaser.objects.filter(
        startup_profile=profile,
        is_current=True,
    ).update(is_current=False, status=TeaserStatus.SUPERSEDED)

    # Инициализируем статус текущего дека
    pitch_deck.processing_state = PitchDeckProcessingState.QUEUED
    pitch_deck.save(update_fields=["processing_state"])

    # Логируем событие
    track(
        EventName.DECK_UPLOADED,
        user=user,
        entity=pitch_deck,
        file_size_bytes=pitch_deck.file_size_bytes,
    )

    # Celery таска
    deck_id = pitch_deck.id
    transaction.on_commit(lambda: process_deck.delay(deck_id))

    return pitch_deck


def processing_status(pitch_deck: PitchDeck) -> str | None:
    """Возвращает статус обработки ИИ ('QUEUED', 'PROCESSING', 'DRAFT_READY', 'FAILED')."""
    if pitch_deck.pk is None or pitch_deck.deleted_at:
        return None
    return pitch_deck.processing_state