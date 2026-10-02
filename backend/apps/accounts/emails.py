from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

VERIFY_SALT = "accounts.email-verify"


def make_verify_token(user):
    return signing.dumps({"uid": user.pk}, salt=VERIFY_SALT)


def read_verify_token(token):
    """Returns user id, raises signing.BadSignature / SignatureExpired."""
    data = signing.loads(token, salt=VERIFY_SALT, max_age=settings.EMAIL_VERIFY_MAX_AGE)
    return data["uid"]


def send_verification_email(user):
    link = f"{settings.FRONTEND_URL}/verify-email?token={make_verify_token(user)}"
    # TODO: final copy / language (DE/UA) once the UI language is decided
    send_mail(
        subject="Confirm your e-mail",
        message=f"Please confirm your e-mail address:\n\n{link}\n\nThe link is valid for 48 hours.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def send_password_reset_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
    send_mail(
        subject="Reset your password",
        message=f"Use this link to set a new password:\n\n{link}\n\nThe link is valid for 1 hour.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
