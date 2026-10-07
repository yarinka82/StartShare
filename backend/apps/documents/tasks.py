import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.analytics.models import EventName
from apps.analytics.services import track



from .models import TeaserJob, Deck
from .teaser.pipeline import build_draft

logger = logging.getLogger(__name__)


def _finish(job, **fields) -> bool:
    """Записать результат, только если задача ещё существует и в PROCESSING.

    Если дек заменили или удалили во время обработки, строки уже нет: результат отбрасывается.
    """
    return TeaserJob.objects.filter(pk=job.pk, state=TeaserJob.State.PROCESSING).update(**fields) == 1


@shared_task
def process_deck(job_id):
    with transaction.atomic():
        job = TeaserJob.objects.select_for_update().filter(pk=job_id).first()
        if job is None or job.state != TeaserJob.State.QUEUED:
            return  # задачи нет (дек заменили) или повторная доставка: ШІ второй раз не вызываем
        job.state = TeaserJob.State.PROCESSING
        job.started_at = timezone.now()
        job.attempts += 1
        job.save(update_fields=["state", "started_at", "attempts"])

    try:
        draft, risk_phrases, cost = build_draft(job)
    except Exception as exc:
        logger.exception("Teaser job %s failed", job_id)
        code = getattr(exc, "code", None)
        # PipelineError уже формата "code: message"; неожиданные ошибки помечаем "unexpected"
        _finish(job, state=TeaserJob.State.FAILED, error=(str(exc) if code else f"unexpected: {exc}")[:2000])
        return

    now = timezone.now()
    processing_ms = int((now - job.started_at).total_seconds() * 1000)
    saved = _finish(job, draft=draft, risk_phrases=risk_phrases, cost_eur=cost, processing_ms=processing_ms,
                    state=TeaserJob.State.DRAFT_READY, ready_at=now)
    if not saved:
        logger.info("Teaser job %s result discarded (deck replaced or deleted)", job_id)
        return
    track(
        EventName.AI_DRAFT_CREATED,
        user=job.deck.profile.user,
        processing_ms=processing_ms,
        risk_phrases_count=len(risk_phrases),
        cost_eur=float(cost) if cost is not None else None,
    )


@shared_task
def purge_expired_decks():
    """REQ-16: удалить файл-оригинал через 24 ч после ai_draft_created (для FAILED: через 24 ч после создания).

    Строка Deck и связанные TeaserJob/Teaser остаются: удаление строки каскадом убило бы тизер.
    """
    cutoff = timezone.now() - timedelta(hours=24)
    expired = Q(ready_at__lt=cutoff) | Q(state=TeaserJob.State.FAILED, created_at__lt=cutoff)
    for job in TeaserJob.objects.filter(expired, original_deleted_at__isnull=True).select_related("deck"):
        deck = job.deck
        if deck.file:
            deck.file.delete(save=False)  # убирает файл из хранилища
        # update(), а не save(): у Deck.uploaded_at стоит auto_now, save() его перезаписал бы
        Deck.objects.filter(pk=deck.pk).update(file="")
        job.original_deleted_at = timezone.now()
        job.save(update_fields=["original_deleted_at"])


@shared_task
def requeue_stuck_jobs():
    cutoff = timezone.now() - timedelta(minutes=15)
    stuck = TeaserJob.objects.filter(state=TeaserJob.State.PROCESSING, started_at__lt=cutoff)
    max_attempts = settings.TEASER_MAX_ATTEMPTS
    stuck.filter(attempts__gte=max_attempts).update(
        state=TeaserJob.State.FAILED, error="timeout: processing timed out")
    ids = list(stuck.filter(attempts__lt=max_attempts).values_list("id", flat=True))
    TeaserJob.objects.filter(id__in=ids).update(state=TeaserJob.State.QUEUED)
    for job_id in ids:
        process_deck.delay(job_id)