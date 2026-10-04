
"""Точки входа для существующей загрузки дека (profiles.Deck)."""
from django.db import transaction

from apps.analytics.events import track
from apps.analytics.models import EventName
from apps.documents.models import Teaser, TeaserJob


def can_replace_deck(profile) -> bool:
    """Замена и удаление дека каскадно убивают тизер. Затверждённый тизер так терять нельзя."""
    return not Teaser.objects.filter(job__deck__profile=profile, status=Teaser.Status.APPROVED).exists()


def start_teaser_job(deck, user) -> TeaserJob:
    """Вызвать из вьюхи загрузки сразу после deck.save(), внутри её transaction.atomic().
    
    При замене дека старая задача и её рабочий тизер удаляются, создаётся новая задача.
    Результат ещё выполняющейся старой задачи будет отброшен (см. tasks._finish).
    """
    from apps.documents.tasks import process_deck
    TeaserJob.objects.filter(deck=deck).delete()
    job = TeaserJob.objects.create(deck=deck)
    track(EventName.DECK_UPLOADED, user=user, file_size_bytes=deck.size)
    transaction.on_commit(lambda: process_deck.delay(job.id))
    return job


def processing_status(deck) -> "str | None":
    """Для DeckSerializer: состояние обработки или None, если задачи нет."""
    if deck.pk is None:  # экземпляр уже удалён
        return None
    return TeaserJob.objects.filter(deck=deck).values_list("state", flat=True).first()