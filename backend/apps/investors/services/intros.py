from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.analytics.models import Event, EventName
from apps.investors.models import Introduction
from apps.investors.services.intro_state_machine import InvalidTransition

# Матриця дозволених переходів строго за ТЗ:
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
    # Будь-який вихід з DECLINED, EXPIRED і INTRODUCED суворо заборонено:
    Introduction.Status.DECLINED: set(),
    Introduction.Status.EXPIRED: set(),
    Introduction.Status.INTRODUCED: set(),
}


def can_transition(current_status: str, target_status: str) -> bool:
    return target_status in ALLOWED_TRANSITIONS.get(current_status, set())


def _get_locked_intro(intro_id: int) -> Introduction:
    """Отримує рядок знайомства з блокуванням рядка в БД (FOR UPDATE)."""
    return Introduction.objects.select_for_update().get(pk=intro_id)


def _log_status_changed(intro: Introduction, prev_status: str, user=None, time_to_react=None):
    """Фіксує аналітичну подію status_changed без персональних даних (I8)."""
    try:
        Event.objects.create(
            name=getattr(EventName, "STATUS_CHANGED", "status_changed"),
            user=user,
            properties={
                "intro_id": intro.id,
                "from_status": prev_status,
                "to_status": intro.status,
                "time_to_react_seconds": time_to_react,
            },
        )
    except Exception:
        pass


# =====================================================================
# 6 МЕТОДІВ ПЕРЕХОДІВ СТАТУСІВ (I1)
# =====================================================================
def interest(intro_id: int, message: str = "", user=None) -> Introduction:
    """
    SUGGESTED -> INTERESTED (інвестор натиснув «Цікаво»).
    Встановлює interested_at та expires_at (now + INTRO_EXPIRE_DAYS).
    """
    with transaction.atomic():
        intro = _get_locked_intro(intro_id)
        prev = intro.status

        now = timezone.now()
        expire_days = getattr(settings, "INTRO_EXPIRE_DAYS", 7)

        intro.status = Introduction.Status.INTERESTED
        intro.interested_at = now
        intro.request_expires_at = now + timedelta(days=expire_days)
        intro.investor_message = message or None
        intro.save()

        _log_status_changed(intro, prev, user=user)
        return intro



def decline_by_investor(intro_id: int, decline_reason=None, user=None) -> Introduction:
    """
    SUGGESTED -> DECLINED (інвестор натиснув «Ні»).
    """
    with transaction.atomic():
        intro = _get_locked_intro(intro_id)
        prev = intro.status

        now = timezone.now()
        intro.status = Introduction.Status.DECLINED
        intro.declined_at = now
        intro.declined_by = Introduction.DeclinedBy.INVESTOR
        if decline_reason:
            intro.decline_reason = decline_reason
        intro.save()

        _log_status_changed(intro, prev, user=user)
        return intro



def accept(intro_id: int, user=None) -> Introduction:
    """
    INTERESTED -> ACCEPTED (стартап натиснув «Freigabe»).
    Перевіряє, що термін request_expires_at ще не минув.
    """
    with transaction.atomic():
        intro = _get_locked_intro(intro_id)
        prev = intro.status
        if prev != Introduction.Status.INTERESTED:
            raise InvalidTransition(f"Cannot accept an intro in status {prev}.")

        now = timezone.now()
        # Перевірка на прострочення
        if intro.request_expires_at and intro.request_expires_at <= now:
            raise InvalidTransition("Термін для відповіді на цей запит уже минув (EXPIRED).")

        time_to_react = int((now - intro.interested_at).total_seconds()) if intro.interested_at else None

        intro.status = Introduction.Status.ACCEPTED
        intro.accepted_at = now
        intro.startup_responded_at = now
        intro.save()

        _log_status_changed(intro, prev, user=user, time_to_react=time_to_react)
        return intro



def decline_by_startup(intro_id: int, user=None) -> Introduction:
    """
    INTERESTED -> DECLINED (стартап натиснув «Nein»).
    Причина за ТЗ не вимагається.
    """
    with transaction.atomic():
        intro = _get_locked_intro(intro_id)
        prev = intro.status

        now = timezone.now()
        time_to_react = int((now - intro.interested_at).total_seconds()) if intro.interested_at else None

        intro.status = Introduction.Status.DECLINED
        intro.declined_at = now
        intro.declined_by = Introduction.DeclinedBy.STARTUP
        intro.startup_responded_at = now
        intro.save()

        _log_status_changed(intro, prev, user=user, time_to_react=time_to_react)
        return intro



def expire(intro_id: int) -> Introduction:
    """
    INTERESTED -> EXPIRED (стартап не відповів за 7 днів або поставив профіль на паузу/видалив).
    """
    with transaction.atomic():
        intro = _get_locked_intro(intro_id)
        prev = intro.status

        now = timezone.now()
        intro.status = Introduction.Status.EXPIRED
        intro.expired_at = now
        intro.save()

        _log_status_changed(intro, prev)
        return intro



def mark_introduced(intro_id: int) -> Introduction:
    """
    ACCEPTED -> INTRODUCED (викликається автоматично після успішної доставки обох листів з контактами).
    """
    with transaction.atomic():
        intro = _get_locked_intro(intro_id)
        prev = intro.status

        now = timezone.now()
        intro.status = Introduction.Status.INTRODUCED
        intro.introduced_at = now
        intro.save()

        _log_status_changed(intro, prev)
        return intro