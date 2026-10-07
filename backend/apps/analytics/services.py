
"""Точки входа для работы с презентациями (PitchDeck) и тизерами."""

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


def can_replace_deck(profile) -> bool:
    """
    Замена и удаление дека блокируются ТОЛЬКО если профиль активен (LIVE).
    Если профиль на паузе (PAUSED) или в черновике (DRAFT) — замена разрешена.
    """
    if getattr(profile, "status", None) == "LIVE":
        return False
    return True


def start_teaser_job(pitch_deck: PitchDeck, user) -> PitchDeck:
    """
    Вызывается сразу после сохранения pitch_deck внутри transaction.atomic().
    
    1. Помечает предыдущие деки как REPLACED (заменённые).
    2. Устанавливает статус QUEUED.
    3. Отправляет задачу в Celery после фиксации транзакции в БД.
    """
    from apps.documents.tasks import process_deck

    profile = pitch_deck.startup_profile

    # Помечаем старые деки этого профиля как заменённые (если они ещё не удалены)
    previous_decks = PitchDeck.objects.filter(
        startup_profile=profile,
        deleted_at__isnull=True,
    ).exclude(pk=pitch_deck.pk)

    for old_deck in previous_decks:
        old_deck.deleted_at = timezone.now()
        old_deck.deletion_reason = PitchDeckDeletionReason.REPLACED
        if old_deck.file:
            old_deck.file.delete(save=False)
        old_deck.storage_key = None
        old_deck.save(update_fields=["deleted_at", "deletion_reason", "storage_key"])

    # Старые тизеры переводятся в SUPERSEDED (заменён)
    Teaser.objects.filter(
        startup_profile=profile,
        is_current=True,
    ).update(is_current=False, status=TeaserStatus.SUPERSEDED)

    # Инициализируем статус текущего дека
    pitch_deck.processing_state = PitchDeckProcessingState.QUEUED
    pitch_deck.save(update_fields=["processing_state"])

    # Логируем аналитическое событие
    track(
        EventName.DECK_UPLOADED,
        user=user,
        file_size_bytes=pitch_deck.file_size_bytes,
    )

    # Запускаем Celery таску после коммита транзакции
    transaction.on_commit(lambda: process_deck.delay(pitch_deck.id))

    return pitch_deck


def processing_status(pitch_deck: PitchDeck) -> "str | None":
    """Возвращает статус обработки ИИ ('QUEUED', 'PROCESSING', 'DRAFT_READY', 'FAILED')."""
    if pitch_deck.pk is None or pitch_deck.deleted_at:
        return None
    return pitch_deck.processing_state