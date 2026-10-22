from datetime import timedelta
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.investors.models import Digest, DigestCard, Introduction, Mandate
from apps.investors.services.matching import find_matches_for_mandate
from apps.investors.services.emails import send_digest_email


@shared_task
def generate_weekly_digests():
    """Щотижнева генерація дайджестів 3–5 тизерів (Celery Beat)."""
    now = timezone.now()
    monday = (now - timedelta(days=now.weekday())).date()

    active_mandates = Mandate.objects.filter(
        is_current=True,
        investor_profile__user__is_active=True,
    ).select_related("investor_profile", "investor_profile__user")

    generated_count = 0

    for mandate in active_mandates:
        inv_profile = mandate.investor_profile

        # Перевірка: тільки один дайджест на поточний тиждень
        if Digest.objects.filter(investor_profile=inv_profile, period_start=monday).exists():
            continue

        matches = find_matches_for_mandate(mandate, limit=5)

        # За ТЗ: відправляємо ТІЛЬКИ якщо є від 3 до 5 тизерів
        if len(matches) < 3:
            continue

        with transaction.atomic():
            digest = Digest.objects.create(
                investor_profile=inv_profile,
                period_start=monday,
                card_count=len(matches),
                sent_at=now,
            )

            for position, match in enumerate(matches, start=1):
                # 🚀 ВИПРАВЛЕНО: передаємо обов'язкові teaser та mandate
                intro, _ = Introduction.objects.get_or_create(
                    investor_profile=inv_profile,
                    startup_profile=match["startup"],
                    defaults={
                        "status": Introduction.Status.SUGGESTED,
                        "teaser": match["teaser"],  # зв'язуємо з затвердженим тизером
                        "mandate": mandate,          # зв'язуємо з версією мандату [B]
                        "suggested_at": now,
                    },
                )

                DigestCard.objects.create(
                    digest=digest,
                    introduction=intro,
                    position=position,
                    match_reason_codes=match["match_reason_codes"],
                    soft_match_count=match["soft_match_count"],
                    profile_age_days=match["profile_age_days"],
                )

            # Відправляємо лист після успішного збереження транзакції
            transaction.on_commit(lambda d=digest, u=inv_profile.user: send_digest_email(u, d))
            generated_count += 1

    return f"Generated {generated_count} weekly digests."



@shared_task
def expire_stale_intro_requests():
    """
    Запускається щоночі.
    Переводить прострочені запити (через 7 днів) зі статусу INTERESTED у EXPIRED.
    """
    now = timezone.now()
    stale_intros = Introduction.objects.filter(
        status=Introduction.Status.INTERESTED,
        request_expires_at__isnull=False,
        request_expires_at__lte=now,
    )
    count = stale_intros.update(
        status="EXPIRED",
        expired_at=now,
    )
    return f"Expired {count} intro requests."

