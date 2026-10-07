import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.analytics.events import track
from apps.analytics.models import EventName
from apps.documents.models import (
    PitchDeck,
    PitchDeckDeletionReason,
    PitchDeckFailureReason,
    PitchDeckProcessingState,
    Teaser,
    TeaserField,
    TeaserFieldFieldName,
    TeaserStatus,
)
from apps.documents.teaser.pipeline import build_draft

logger = logging.getLogger(__name__)


@shared_task
def process_deck(deck_id: int):
    """
    Основная фоновая задача: извлекает текст из PDF, отправляет в Gemini
    и создаёт Teaser со всеми языковыми полями TeaserField.
    """
    # 1. Атомарно переводим дек в состояние PROCESSING
    with transaction.atomic():
        pitch_deck = (
            PitchDeck.objects.select_for_update()
            .select_related("startup_profile__user")
            .filter(pk=deck_id)
            .first()
        )
        if pitch_deck is None or pitch_deck.processing_state != PitchDeckProcessingState.QUEUED:
            return  # Дек удалён/заменён или уже взят в работу

        pitch_deck.processing_state = PitchDeckProcessingState.PROCESSING
        pitch_deck.processing_started_at = timezone.now()
        pitch_deck.attempt_count += 1
        pitch_deck.save(update_fields=["processing_state", "processing_started_at", "attempt_count"])

    profile = pitch_deck.startup_profile
    user = profile.user

    # 2. Вызываем LLM-пайплайн
    try:
        draft, risk_phrases, cost = build_draft(pitch_deck)
    except Exception as exc:
        logger.exception("Pitch deck processing failed for deck #%s", deck_id)
        code = getattr(exc, "code", None)

        # Сопоставляем ошибку с FailureReason
        failure_reason = PitchDeckFailureReason.OTHER
        if code in ("corrupted", "encrypted", "no_text", "empty", "pdf_unreadable"):
            failure_reason = PitchDeckFailureReason.PDF_UNREADABLE
        elif code in ("invalid_response", "json_error"):
            failure_reason = PitchDeckFailureReason.INVALID_RESPONSE
        elif code in ("provider_unavailable", "503", "timeout", "llm_error"):
            failure_reason = PitchDeckFailureReason.PROVIDER_UNAVAILABLE

        with transaction.atomic():
            PitchDeck.objects.filter(pk=deck_id, processing_state=PitchDeckProcessingState.PROCESSING).update(
                processing_state=PitchDeckProcessingState.FAILED,
                failure_reason=failure_reason,
                processing_finished_at=timezone.now(),
            )
        return

    # 3. Сохраняем успешный результат генерации
    now = timezone.now()
    processing_ms = int((now - pitch_deck.processing_started_at).total_seconds() * 1000)

    with transaction.atomic():
        # Проверяем, что дек не был заменён или удалён пользователем во время генерации
        updated = PitchDeck.objects.filter(
            pk=deck_id, processing_state=PitchDeckProcessingState.PROCESSING
        ).update(
            processing_state=PitchDeckProcessingState.DRAFT_READY,
            processing_finished_at=now,
            ai_cost_eur=cost,
            delete_after=now + timedelta(hours=24),  # Автоудаление оригинала ровно через 24 часа
        )

        if not updated:
            logger.info("Pitch deck #%s result discarded (replaced or deleted while processing)", deck_id)
            return

        # Переводим старые тизеры этого стартапа в SUPERSEDED
        Teaser.objects.filter(startup_profile=profile, is_current=True).update(
            is_current=False, status=TeaserStatus.SUPERSEDED
        )

        # Вычисляем номер следующей версии тизера (v1, v2, v3...)
        last_version = (
            Teaser.objects.filter(startup_profile=profile).order_by("-version").values_list("version", flat=True).first() or 0
        )
        new_version = last_version + 1

        # Создаём новую версию тизера
        teaser = Teaser.objects.create(
            startup_profile=profile,
            pitch_deck=pitch_deck,
            version=new_version,
            status=TeaserStatus.DRAFT,
            is_current=True,
        )

        # Создаём поля тизера (TeaserField)
        teaser_content = draft.get("teaser", {}) if isinstance(draft, dict) else draft
        for field_name, text in teaser_content.items():
            if field_name in TeaserFieldFieldName.values:
                # Фильтруем рисковые фразы, относящиеся к этому полю
                field_risks = [
                    r for r in risk_phrases
                    if isinstance(r, dict) and r.get("field") == field_name or r.get("category")
                ]
                TeaserField.objects.create(
                    teaser=teaser,
                    field_name=field_name,
                    language="de",
                    ai_text=text or "",
                    final_text=text or "",
                    risk_phrases=field_risks,
                )

    # 4. Аналитическое событие
    track(
        EventName.AI_DRAFT_CREATED,
        user=user,
        processing_ms=processing_ms,
        risk_phrases_count=len(risk_phrases),
        cost_eur=float(cost) if cost is not None else None,
    )


@shared_task
def purge_expired_decks():
    """
    24h Retention Policy (GDPR):
    Удаляет физический файл PDF через 24 часа после завершения обработки,
    если стартап не выбрал флаг keep_original=True.
    Метаданные PitchDeck остаются для аудита с пометкой AUTO_24H.
    """
    now = timezone.now()
    expired_decks = PitchDeck.objects.filter(
        delete_after__lte=now,
        deleted_at__isnull=True,
        keep_original=False,
    )

    for deck in expired_decks:
        if deck.file:
            deck.file.delete(save=False)

        deck.deleted_at = now
        deck.deletion_reason = PitchDeckDeletionReason.AUTO_24H
        deck.storage_key = None
        deck.save(update_fields=["deleted_at", "deletion_reason", "storage_key"])

    logger.info("Purged %d expired pitch deck files.", expired_decks.count())


@shared_task
def requeue_stuck_jobs():
    """Перезапускает зависшие задачи (например, если воркер упал по OOM)."""
    cutoff = timezone.now() - timedelta(minutes=15)
    max_attempts = getattr(settings, "TEASER_MAX_ATTEMPTS", 3)

    stuck = PitchDeck.objects.filter(
        processing_state=PitchDeckProcessingState.PROCESSING,
        processing_started_at__lt=cutoff,
    )

    # Превысившие число попыток помечаем FAILED
    stuck.filter(attempt_count__gte=max_attempts).update(
        processing_state=PitchDeckProcessingState.FAILED,
        failure_reason=PitchDeckFailureReason.PROVIDER_UNAVAILABLE,
        processing_finished_at=timezone.now(),
    )

    # Зависшие, у которых ещё есть попытки, возвращаем в очередь QUEUED
    retry_ids = list(stuck.filter(attempt_count__lt=max_attempts).values_list("id", flat=True))
    PitchDeck.objects.filter(id__in=retry_ids).update(processing_state=PitchDeckProcessingState.QUEUED)

    for deck_id in retry_ids:
        process_deck.delay(deck_id)