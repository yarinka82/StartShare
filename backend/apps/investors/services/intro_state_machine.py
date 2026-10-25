from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.analytics.models import Event, EventName
from apps.investors.models import Introduction


class InvalidTransition(APIException):
    """Кидається при спробі нерозрешеного переходу статусу (в API це 409 Conflict)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Цей перехід статусу не дозволений правилами платформи."
    
    
class InvalidTransitionError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Цей перехід статусу заборонений правилами платформи."


# Матриця дозволених переходів за ТЗ
ALLOWED_TRANSITIONS = {
    Introduction.Status.SUGGESTED: {
        Introduction.Status.INTERESTED,
        Introduction.Status.DECLINED,
    },
    Introduction.Status.INTERESTED: {
        Introduction.Status.ACCEPTED,
        Introduction.Status.DECLINED,
        Introduction.Status.EXPIRED,
    },
    Introduction.Status.ACCEPTED: {
        Introduction.Status.INTRODUCED,
    },
    # Фінальні статуси (вихід заборонено):
    Introduction.Status.DECLINED: set(),
    Introduction.Status.EXPIRED: set(),
    Introduction.Status.INTRODUCED: set(),
}


def can_transition(current_status: str, target_status: str) -> bool:
    return target_status in ALLOWED_TRANSITIONS.get(current_status, set())


def transition_introduction(intro_id: int, target_status: str, user=None, **kwargs) -> Introduction:
    """
    Єдина точка входу для зміни статусу Introduction (I1).
    Захист від race conditions через select_for_update.
    """
    with transaction.atomic():
        intro = (
            Introduction.objects.select_for_update()
            .select_related("investor_profile__user", "startup_profile__user")
            .get(pk=intro_id)
        )

        current = intro.status

        # 1. Перевірка дозволу переходу за матрицею
        if not can_transition(current, target_status):
            raise InvalidTransitionError(
                f"Неможливо перейти зі статусу '{current}' у '{target_status}'."
            )

        now = timezone.now()
        update_fields = ["status", "updated_at"]
        intro.status = target_status
        intro.updated_at = now

        # Розрахунок часу реакції для аналітики
        time_to_react = None

        # 2. Обробка специфічних переходів
        if target_status == Introduction.Status.INTERESTED:
            intro.interested_at = now
            expire_days = getattr(settings, "INTRO_EXPIRE_DAYS", 7)
            intro.request_expires_at = now + timedelta(days=expire_days)
            intro.investor_message = kwargs.get("message", "")
            update_fields.extend(["interested_at", "request_expires_at", "investor_message"])

        elif target_status == Introduction.Status.ACCEPTED:
            # Перевірка: чи не минув термін дії запиту
            if intro.request_expires_at and intro.request_expires_at < now:
                raise InvalidTransitionError("Термін відповіді на цей запит уже закінчився (EXPIRED).")

            intro.accepted_at = now
            intro.startup_responded_at = now
            if intro.interested_at:
                time_to_react = int((now - intro.interested_at).total_seconds())
            update_fields.extend(["accepted_at", "startup_responded_at"])

        elif target_status == Introduction.Status.INTRODUCED:
            intro.introduced_at = now
            update_fields.append("introduced_at")

        elif target_status == Introduction.Status.DECLINED:
            declined_by = kwargs.get("declined_by", "investor")
            intro.declined_at = now
            intro.declined_by = declined_by
            update_fields.extend(["declined_at", "declined_by"])

            if declined_by == "startup":
                intro.startup_responded_at = now
                if intro.interested_at:
                    time_to_react = int((now - intro.interested_at).total_seconds())
                update_fields.append("startup_responded_at")

            if kwargs.get("decline_reason"):
                intro.decline_reason = kwargs.get("decline_reason")
                update_fields.append("decline_reason")

        elif target_status == Introduction.Status.EXPIRED:
            intro.expired_at = now
            update_fields.append("expired_at")

        intro.save(update_fields=update_fields)

        # 3. Логування події зміни статусу за ТЗ (без персональних даних!)
        try:
            Event.objects.create(
                name=EventName.STATUS_CHANGED if hasattr(EventName, "STATUS_CHANGED") else "status_changed",
                user=user,
                properties={
                    "intro_id": intro.id,
                    "from_status": current,
                    "to_status": target_status,
                    "time_to_react_seconds": time_to_react,
                },
            )
        except Exception:
            pass

        return intro