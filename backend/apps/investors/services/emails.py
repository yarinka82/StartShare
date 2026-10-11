import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
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