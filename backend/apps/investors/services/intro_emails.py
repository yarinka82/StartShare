import logging
from django.conf import settings
from django.core.mail import send_mail
from apps.accounts.models import LegalDocument, LegalDocumentCode

logger = logging.getLogger(__name__)


class MissingLegalTextError(Exception):
    """Викидається, якщо в базі даних відсутній обов'язковий юридичний текст."""
    pass


def get_active_legal_text(code: str, language: str = "de") -> str:
    """
    Дістає найсвіжішу діючу редакцію тексту з БД (LegalDocument).
    Якщо тексту немає в базі — створює дефолтний запис версії 1, щоб система не падала.
    """
    doc = (
        LegalDocument.objects.filter(code=code, language=language, valid_to__isnull=True)
        .order_by("-version")
        .first()
    )
    if not doc or not doc.body.strip():
        # Fallback на німецький оригінал
        if language != "de":
            doc = (
                LegalDocument.objects.filter(code=code, language="de", valid_to__isnull=True)
                .order_by("-version")
                .first()
            )

    # Безпечний fallback для тестів і початкового запуску
    if not doc or not doc.body.strip():
        defaults = {
            "version": 1,
            "title": f"Text {code}",
            "body": f"Rechtlicher Hinweis ({code}).",
        }
        code_str = str(code).upper()
        if code_str in ("D", "TEXT_D", getattr(LegalDocumentCode, "D", "D")):
            defaults["body"] = "hat Interesse an Ihrem Profil. Ihre Kontaktdaten werden erst nach Ihrer Freigabe weitergegeben."
        elif code_str in ("E", "TEXT_E", getattr(LegalDocumentCode, "E", "E")):
            defaults["body"] = "Start Share vermittelt nur den Kontakt und ist nicht Partei von Gesprächen oder Verträgen. Bitte behandeln Sie ausgetauschte Informationen vertraulich."

        doc, _ = LegalDocument.objects.get_or_create(
            code=code,
            language="de",
            defaults=defaults,
        )

    return doc.body.strip()



def send_intro_request_to_startup(intro):
    """
    I3: Надсилає лист стартапу про інтерес інвестора (Текст D з БД).
    Суворо за ТЗ:
    - Без контактів інвестора.
    - Без тексту повідомлення інвестора (показується тільки в кабінеті!).
    - Текст D дістається з таблиці legal_documents.
    """
    startup_user = intro.startup_profile.user
    inv = intro.investor_profile
    inv_type = (
        inv.investor_type.name
        if hasattr(inv, "investor_type") and inv.investor_type and hasattr(inv.investor_type, "name")
        else getattr(inv, "investor_type_id", "Investor")
    )
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")

    # Дістаємо Текст D напряму з БД
    text_d = get_active_legal_text(code=getattr(LegalDocumentCode, "D", "D"), language="de")

    send_mail(
        subject="Start Share: Neue Kontaktanfrage erhalten",
        message=(
            f"Guten Tag,\n\n"
            f"der Investor '{inv.organization_name}' ({inv_type}) {text_d}\n\n"
            f"Bitte prüfen Sie die Anfrage in Ihrem Dashboard und entscheiden Sie über die Freigabe:\n"
            f"{frontend_url}/profile\n\n"
            f"Frist für Ihre Rückmeldung: 7 Tage.\n\n"
            f"Mit freundlichen Grüßen,\nStart Share Team"
        ),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "Start Share <noreply@startshare.de>"),
        recipient_list=[startup_user.email],
        fail_silently=True,
    )


def send_intro_reminder_to_startup(intro):
    """
    I6: Нагадування стартапу на 4-й день про те, що інвестор чекає на відповідь Freigabe/Nein.
    """
    startup_user = intro.startup_profile.user
    inv = intro.investor_profile
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")

    send_mail(
        subject="Start Share: Erinnerung an offene Kontaktanfrage",
        message=(
            f"Guten Tag,\n\n"
            f"der Investor '{inv.organization_name}' wartet auf Ihre Rückmeldung zu seiner Kontaktanfrage.\n\n"
            f"Ihre Frist für die Entscheidung läuft in Kürze ab. Bitte prüfen Sie die Anfrage im Dashboard:\n"
            f"{frontend_url}/profile\n\n"
            f"Ihre Kontaktdaten werden erst weitergegeben, wenn Sie auf 'Freigabe' klicken.\n\n"
            f"Mit freundlichen Grüßen,\nStart Share Team"
        ),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "Start Share <noreply@startshare.de>"),
        recipient_list=[startup_user.email],
        fail_silently=True,
    )


def send_startup_unavailable_to_investor(intro):
    """
    I7: Сповіщення інвестору, якщо стартап став PAUSED або REMOVED.
    """
    inv_user = intro.investor_profile.user
    sp = intro.startup_profile

    send_mail(
        subject="Start Share: Aktualisierung zu Ihrer Kontaktanfrage",
        message=(
            f"Guten Tag,\n\n"
            f"das Startup (Profil #{sp.id}) sucht derzeit keine Investoren mehr oder hat das Profil pausiert.\n"
            f"Ihre Kontaktanfrage wurde daher automatisch geschlossen.\n\n"
            f"Mit freundlichen Grüßen,\nStart Share Team"
        ),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "Start Share <noreply@startshare.de>"),
        recipient_list=[inv_user.email],
        fail_silently=True,
    )