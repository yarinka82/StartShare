import logging
from django.conf import settings
from django.core import mail, signing
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)

VERIFY_SALT = "email-verify"


def make_verify_token(user) -> str:
    # the email is inside: after an address change the old link stops working
    return signing.dumps({"uid": user.pk, "email": user.email}, salt=VERIFY_SALT)


def read_verify_token(token: str):
    """Returns the payload or None (expired / tampered)."""
    try:
        return signing.loads(token, salt=VERIFY_SALT, max_age=settings.EMAIL_VERIFY_MAX_AGE)
    except signing.BadSignature:  # SignatureExpired is a subclass
        return None


def _send(subject: str, body: str, to: str) -> None:
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=False)
    except Exception:
        # a mail failure must not turn registration into a 500; the user can ask for a resend
        logger.exception("Could not send e-mail to user")
        raise


def _commit_or_send(callback) -> None:
    """
    В тестах выполняет отправку сразу (так как TestCase откатывает транзакции).
    На проде выполняет безопасно только после коммита в БД.
    """
    if hasattr(mail, "outbox"):
        callback()
    else:
        transaction.on_commit(callback)


def send_verification_email(user) -> None:
    link = f"{settings.FRONTEND_URL}/verify-email?token={make_verify_token(user)}"
    body = (
        "Willkommen bei StartShare!\n\n"
        f"Bitte bestätigen Sie Ihre E-Mail-Adresse (Link 48 Stunden gültig):\n{link}\n\n"
        "Wenn Sie sich nicht registriert haben, ignorieren Sie diese Nachricht."
    )
    _commit_or_send(lambda: _send("E-Mail-Adresse bestätigen", body, user.email))


def send_password_reset_email(user) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
    body = (
        "Sie haben das Zurücksetzen Ihres Passworts angefordert (Link 1 Stunde gültig):\n"
        f"{link}\n\nWenn Sie das nicht waren, ignorieren Sie diese Nachricht."
    )
    _commit_or_send(lambda: _send("Passwort zurücksetzen", body, user.email))
