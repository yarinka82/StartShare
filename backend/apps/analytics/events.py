import logging

from django.db import transaction

from .models import Event, EventName

logger = logging.getLogger(__name__)


def track(name: EventName, user=None, **properties) -> None:
    """Record a product event. Never raises: analytics must not break a user request.

    The savepoint keeps a failed insert from poisoning the surrounding transaction.
    """
    try:
        with transaction.atomic():
            Event.objects.create(name=name, user=user, properties=properties)
    except Exception:  # noqa: BLE001
        logger.exception("could not record event %s", name)
