import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def send_digest_email(user, digest):
    """
    Відправляє щотижневий дайджест інвестору на DE або EN
    з обов'язковим Дисклеймером B.
    """
    # 🚀 Порт за замовчуванням виправлено на 5173 (Vite)
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    
    # Посилання веде в стрічку інвестора
    digest_url = f"{frontend_url}/investor/feed"
    
    user_lang = getattr(user, "preferred_language", "de")
    if user_lang not in ("de", "en"):
        user_lang = "de"
    
    subjects = {
        "de": f"StartShare: Neuer wöchentlicher Startup-Digest ({digest.card_count} Teaser)",
        "en": f"StartShare: Your weekly startup digest ({digest.card_count} teasers)",
    }
    
    template_name = f"emails/digest_notification_{user_lang}.html"
    
    first_name = getattr(user, "first_name", None)
    if not first_name:
        first_name = user.email.split("@")[0] if getattr(user, "email", None) else "Investor"
    
    # Завантажуємо картки для підстановки в шаблон
    cards = digest.cards.select_related(
        "introduction__startup_profile",
        "introduction__teaser"
    ).order_by("position")
    
    context = {
        "user": user,
        "first_name": first_name,
        "digest": digest,
        "cards": cards,
        "card_count": digest.card_count,
        "digest_url": digest_url,
        # Обов'язковий текст Дисклеймера B
        "disclaimer_b": "Angaben des Startups, nicht von Start Share geprüft. Keine Anlageberatung, keine Empfehlung und kein Angebot zum Erwerb von Beteiligungen.",
    }
    
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)
    
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "StartShare <noreply@startshare.de>")
    subject = subjects.get(user_lang, subjects["de"])
    
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[user.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        logger.info(f"Digest email ({user_lang.upper()}) sent to {user.email} (Digest #{digest.id})")
    except Exception as e:
        logger.error(f"Failed to send digest email to {user.email}: {e}", exc_info=True)
        
        
        
TEXT_E = (
    "Start Share vermittelt nur den Kontakt und ist nicht Partei von Gesprächen oder Verträgen. "
    "Bitte behandeln Sie ausgetauschte Informationen vertraulich."
)


def send_intro_completed_emails(intro):
    """
    Надсилає обом сторонам контакти одна одної та Текст E (Art. E).
    Викликається тільки після того, як стартап натиснув 'Freigabe'.
    """
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Start Share <noreply@startshare.de>")

    inv_profile = intro.investor_profile
    investor_user = inv_profile.user
    sp_profile = intro.startup_profile
    startup_user = sp_profile.user

    # Отримуємо назву компанії стартапу (з моделі або приватних деталей)
    company_name = getattr(sp_profile, "company_name", "")
    if hasattr(sp_profile, "private_details") and sp_profile.private_details:
        company_name = sp_profile.private_details.company_name or company_name
    if not company_name:
        company_name = f"Startup #{sp_profile.id}"

    # Контакти інвестора
    inv_org = inv_profile.organization_name
    inv_contact = inv_profile.contact_person_name or "Investment Team"
    inv_email = inv_profile.contact_email or investor_user.email

    # 1. Лист інвестору з контактами стартапу
    send_mail(
        subject=f"Start Share: Kontaktfreigabe erteilt für {company_name}",
        message=(
            f"Guten Tag {inv_contact},\n\n"
            f"das Startup '{company_name}' (Profil #{sp_profile.id}) hat Ihre Kontaktanfrage angenommen!\n\n"
            f"Kontaktdaten des Gründers:\n"
            f"E-Mail: {startup_user.email}\n\n"
            f"Sie können nun direkt per E-Mail in Kontakt treten.\n\n"
            f"---\n"
            f"Rechtlicher Hinweis:\n{TEXT_E}"
        ),
        from_email=from_email,
        recipient_list=[investor_user.email],
        fail_silently=True,
    )

    # 2. Лист стартапу з контактами інвестора
    send_mail(
        subject=f"Start Share: Kontaktdaten von {inv_org}",
        message=(
            f"Guten Tag,\n\n"
            f"Sie haben die Kontaktdaten für {inv_org} freigegeben.\n\n"
            f"Kontaktdaten des Investors:\n"
            f"Organisation: {inv_org}\n"
            f"Ansprechpartner: {inv_contact}\n"
            f"E-Mail: {inv_email}\n\n"
            f"Der Investor hat ebenfalls Ihre E-Mail-Adresse erhalten.\n\n"
            f"---\n"
            f"Rechtlicher Hinweis:\n{TEXT_E}"
        ),
        from_email=from_email,
        recipient_list=[startup_user.email],
        fail_silently=True,
    )