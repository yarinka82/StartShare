
import logging

from django.db import transaction

from .models import Event

logger = logging.getLogger(__name__)


def track(name, user=None, **properties):
    """Записать событие. Сбой аналитики не должен ломать основной сценарий."""
    try:
        with transaction.atomic():  # savepoint: ошибка записи не отравит внешнюю транзакцию
            Event.objects.create(name=name, user=user, properties=properties)
    except Exception:
        logger.exception("Failed to log event %s", name)