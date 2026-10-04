import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.analytics.models import EventName
from apps.analytics.services import track

from .models import TeaserJob
from .teaser.pipeline import build_draft

logger = logging.getLogger(__name__)


@shared_task
def process_deck(job_id):
    with transaction.atomic():
        job = TeaserJob.objects.select_for_update().get(pk=job_id)
        if job.state != TeaserJob.State.QUEUED:
            return  # идемпотентность: повторная доставка не вызывает ШІ дважды
        job.state = TeaserJob.State.PROCESSING
        job.started_at = timezone.now()
        job.attempts += 1
        job.save(update_fields=["state", "started_at", "attempts"])
    
    try:
        draft, risk_phrases, cost = build_draft(job)
    except Exception as exc:
        logger.exception("Teaser job %s failed", job_id)
        code = getattr(exc, "code", None)
        job.state = TeaserJob.State.FAILED
        # PipelineError уже формата "code: message"; неожиданные ошибки помечаем "unexpected"
        job.error = (str(exc) if code else f"unexpected: {exc}")[:2000]
        job.save(update_fields=["state", "error"])
        return
    
    now = timezone.now()
    job.draft = draft
    job.risk_phrases = risk_phrases
    job.cost_eur = cost
    job.processing_ms = int((now - job.started_at).total_seconds() * 1000)
    job.state = TeaserJob.State.DRAFT_READY
    job.ready_at = now
    job.save(update_fields=["draft", "risk_phrases", "cost_eur", "processing_ms", "state", "ready_at"])
    track(
        EventName.AI_DRAFT_CREATED,
        user=job.deck.startup.user,
        processing_ms=job.processing_ms,
        risk_phrases_count=len(risk_phrases),
        cost_eur=float(cost) if cost is not None else None,
    )


@shared_task
def purge_expired_decks():
    """REQ-16: удалить оригинал через 24 ч после ai_draft_created."""
    cutoff = timezone.now() - timedelta(hours=24)
    jobs = (TeaserJob.objects.filter(ready_at__lt=cutoff, deck__deleted_at__isnull=True)
            .select_related("deck"))
    for job in jobs:
        deck = job.deck
        if deck.file:
            deck.file.delete(save=False)
        deck.file = ""
        deck.deleted_at = timezone.now()
        deck.save(update_fields=["file", "deleted_at"])


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