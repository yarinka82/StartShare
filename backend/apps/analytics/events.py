import logging
from typing import Any
from django.db import transaction

from .models import Event, EventName, EventRole

logger = logging.getLogger(__name__)


def track(
    name: EventName | str,
    user: Any = None,
    role: EventRole | str | None = None,
    entity: Any = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    **properties,
) -> None:
    try:
        # Извлекаем User объект, если он передан
        user_obj = user if hasattr(user, "pk") else None
        user_id = user.pk if user_obj else user

        # Определяем роль
        if not role:
            if hasattr(user, "role") and user.role:
                role = str(user.role).lower()
            elif user_id:
                role = EventRole.INVESTOR
            else:
                role = EventRole.SYSTEM

        # ВАЖНО: сохраняем role в properties для обратной совместимости с тестами
        if role and "role" not in properties:
            properties["role"] = role

        # entity_type и entity_id
        if entity and hasattr(entity, "_meta"):
            entity_type = entity_type or entity._meta.model_name
            entity_id = entity_id or getattr(entity, "pk", None)

        with transaction.atomic():
            kwargs = {
                "name": name,
                "role": role,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "properties": properties,
            }
            if user_obj:
                kwargs["user"] = user_obj
            elif user_id:
                kwargs["user_id"] = user_id

            Event.objects.create(**kwargs)
    except Exception:  # noqa: BLE001
        logger.exception("could not record event %s", name)
