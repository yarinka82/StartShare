
"""Точки входа для существующей загрузки дека (profiles.Deck)."""
from django.db import transaction

from apps.analytics.events import track
from apps.analytics.models import EventName
from apps.documents.models import Teaser, TeaserJob


def can_replace_deck(profile) -> bool:
    """
    Заміна та видалення дека блокуються ТІЛЬКИ тоді, коли профіль активний (LIVE).
    Якщо профіль на паузі (PAUSED) або чернетка (DRAFT) — заміна дозволена.
    """
    # 1. Якщо профіль активний для інвесторів (LIVE) — видаляти дек ЗАБОРОНЕНО
    if getattr(profile, "status", None) == "LIVE":
        return False

    # 2. Якщо профіль на паузі (PAUSED) чи DRAFT — видаляти та замінювати МОЖНА
    return True


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