from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from celery import shared_task

from apps.accounts.models import LegalDocumentCode, PlatformConfig
from apps.investors.models import Digest, DigestCard, Introduction, Mandate
from apps.investors.services import intros
from apps.investors.services.intro_emails import get_active_legal_text, MissingLegalTextError, \
    send_intro_reminder_to_startup
from apps.investors.services.intro_state_machine import transition_introduction
from apps.investors.services.matching import find_matches_for_mandate
from apps.investors.services.emails import send_digest_email

import logging

logger = logging.getLogger(__name__)


def build_digest_for_mandate(mandate, *, now=None):
    """One investor: returns the new Digest, or None if nothing to send."""
    now = now or timezone.now()
    today = timezone.localdate(now)
    monday = today - timedelta(days=today.weekday())
    inv_profile = mandate.investor_profile

    if Digest.objects.filter(investor_profile=inv_profile, period_start=monday).exists():
        return None

    cfg = PlatformConfig.get_solo()
    matches = find_matches_for_mandate(mandate, limit=cfg.max_digest_cards)
    if len(matches) < cfg.min_digest_cards:
        return None

    with transaction.atomic():
        digest = Digest.objects.create(
            investor_profile=inv_profile, period_start=monday, card_count=len(matches),
        )
        for position, match in enumerate(matches, start=1):
            intro, _ = Introduction.objects.get_or_create(
                investor_profile=inv_profile,
                startup_profile=match["startup"],
                defaults={
                    "status": Introduction.Status.SUGGESTED,
                    "teaser": match["teaser"],
                    "mandate": mandate,
                    "suggested_at": now,
                },
            )
            DigestCard.objects.create(
                digest=digest, introduction=intro, position=position,
                match_reason_codes=match["match_reason_codes"],
                soft_match_count=match["soft_match_count"],
                profile_age_days=match["profile_age_days"],
            )
        # a mail failure must not break the digest (or the loop over other investors)
        transaction.on_commit(
            lambda: send_digest_email(inv_profile.user, digest), robust=True,
        )
    return digest



@shared_task
def generate_weekly_digests():
    now = timezone.now()
    mandates = Mandate.objects.filter(
        is_current=True, investor_profile__user__is_active=True,
    ).select_related("investor_profile", "investor_profile__user")

    generated = 0
    for mandate in mandates:
        try:
            if build_digest_for_mandate(mandate, now=now):
                generated += 1
        except Exception:
            logger.exception("Digest failed for investor_profile=%s", mandate.investor_profile_id)
    return f"Generated {generated} weekly digests."



@shared_task
def build_first_digest(investor_profile_id: int):
    """Right after the first mandate save: do not make a new investor wait until Monday."""
    mandate = (
        Mandate.objects.select_related("investor_profile", "investor_profile__user")
        .filter(investor_profile_id=investor_profile_id, is_current=True)
        .first()
    )
    if mandate is None:
        return "no current mandate"
    try:
        digest = build_digest_for_mandate(mandate)
    except Exception:
        logger.exception("First digest failed for investor_profile=%s", investor_profile_id)
        return "failed"
    return f"digest {digest.pk}" if digest else "nothing to send"



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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_intro(self, introduction_id: int):
    """
    I5: Celery-задача відправки контактів та Тексту E.
    - Текст E дістається виключно з БД (якщо нема — лист не йде).
    - Перевіряє статус ACCEPTED та що акаунти активні й не REMOVED.
    - Ідемпотентність: sent_to_startup та sent_to_investor захищають від дублів.
    - Тільки після успіху обох листів: ACCEPTED -> INTRODUCED.
    """
    try:
        intro = (
            Introduction.objects
            .select_related("investor_profile__user", "startup_profile__user", "startup_profile")
            .get(pk=introduction_id)
        )
        
        # 1. Перевірка статусу: відправка можлива тільки для ACCEPTED
        if intro.status != Introduction.Status.ACCEPTED:
            return f"Skipped: Status is {intro.status}, expected ACCEPTED"
        
        inv_profile = intro.investor_profile
        sp_profile = intro.startup_profile
        inv_user = inv_profile.user
        sp_user = sp_profile.user
        
        # 2. Перевірка видалення акаунтів (GDPR Art. 17 важливіший за Freigabe)
        if not inv_user.is_active or not sp_user.is_active or sp_profile.status == "REMOVED":
            return "Skipped: One of the accounts was removed or deactivated."
        
        # 3. Отримуємо Текст E з БД (якщо в базі нема — викидаємо помилку, лист не піде!)
        user_lang = getattr(inv_user, "preferred_language", "de")
        text_e = get_active_legal_text(code=LegalDocumentCode.E, language=user_lang)
        
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Start Share <noreply@startshare.de>")
        
        # Контакти стартапу
        company_name = getattr(sp_profile, "company_name", "")
        if hasattr(sp_profile, "private_details") and sp_profile.private_details:
            company_name = sp_profile.private_details.company_name or company_name
        if not company_name:
            company_name = f"Startup #{sp_profile.id}"
        
        # Контакти інвестора
        inv_org = inv_profile.organization_name
        inv_contact = inv_profile.contact_person_name or "Investment Team"
        inv_email = inv_profile.contact_email or inv_user.email
        
        # 4. Лист інвестору (з захистом від повтору)
        if not intro.intro_email_sent_to_investor:
            send_mail(
                subject=f"Start Share: Kontaktfreigabe erteilt für {company_name}",
                message=(
                    f"Guten Tag {inv_contact},\n\n"
                    f"das Startup '{company_name}' (Profil #{sp_profile.id}) hat Ihre Kontaktanfrage angenommen!\n\n"
                    f"Kontaktdaten des Gründers:\n"
                    f"Organisation: {company_name}\n"
                    f"E-Mail: {sp_user.email}\n\n"
                    f"Sie können nun direkt in Kontakt treten.\n\n"
                    f"---\n"
                    f"Rechtlicher Hinweis (Text E aus der Datenbank):\n"
                    f"{text_e}"
                ),
                from_email=from_email,
                recipient_list=[inv_user.email],
                fail_silently=False,
            )
            intro.intro_email_sent_to_investor = True
            intro.save(update_fields=["intro_email_sent_to_investor"])
        
        # 5. Лист стартапу (з захистом від повтору)
        if not intro.intro_email_sent_to_startup:
            send_mail(
                subject=f"Start Share: Kontaktdaten von {inv_org}",
                message=(
                    f"Guten Tag,\n\n"
                    f"Sie haben den Kontakt zu {inv_org} freigegeben.\n\n"
                    f"Kontaktdaten des Investors:\n"
                    f"Organisation: {inv_org}\n"
                    f"Ansprechpartner: {inv_contact}\n"
                    f"E-Mail: {inv_email}\n\n"
                    f"---\n"
                    f"Rechtlicher Hinweis (Text E aus der Datenbank):\n"
                    f"{text_e}"
                ),
                from_email=from_email,
                recipient_list=[sp_user.email],
                fail_silently=False,
            )
            intro.intro_email_sent_to_startup = True
            intro.save(update_fields=["intro_email_sent_to_startup"])
        
        # 6. Тільки коли обидва листи відправлені: ACCEPTED -> INTRODUCED через State Machine (I1)
        if intro.intro_email_sent_to_investor and intro.intro_email_sent_to_startup:
            intros.mark_introduced(intro.id)
        
        return f"Intro #{intro.id} successfully marked as INTRODUCED."
    
    except MissingLegalTextError as exc:
        logger.error("Intro task aborted: %s", exc)
        raise exc  # Не надсилаємо без Тексту E за ТЗ!
    except Exception as exc:
        logger.error("Failed sending intro emails (attempt %d): %s", self.request.retries, exc)
        raise self.retry(exc=exc)



@shared_task
def process_intro_timeouts_and_reminders():
    """
    I6: Щоденна таска (Celery Beat):
    1. EXPIRED через 7 днів
    2. Нагадування на 4-й день
    """
    now = timezone.now()

    # 1. Запити, де термін минув -> EXPIRED
    expired = Introduction.objects.filter(
        status=Introduction.Status.INTERESTED,
        request_expires_at__lte=now,
    )
    for intro in expired:
        transition_introduction(intro.id, Introduction.Status.EXPIRED)

    # 2. Нагадування на 4-й день (без повторів)
    try:
        from apps.accounts.models import PlatformConfig
        reminder_days = PlatformConfig.get_solo().intro_reminder_days
    except Exception:
        reminder_days = getattr(settings, "INTRO_REMINDER_DAYS", 4)
    
    threshold = now - timedelta(days=reminder_days)

    need_reminder = Introduction.objects.filter(
        status=Introduction.Status.INTERESTED,
        interested_at__lte=threshold,
        reminder_sent_at__isnull=True,
    )
    for intro in need_reminder:
        send_intro_reminder_to_startup(intro)
        intro.reminder_sent_at = now
        intro.save(update_fields=["reminder_sent_at"])