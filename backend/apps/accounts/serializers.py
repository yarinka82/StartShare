from django.contrib.auth.password_validation import validate_password as run_password_validators
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import translation
from django.utils.translation import ngettext
from rest_framework import serializers

from .models import Role


# NOTE: custom validation messages are stable error codes (e.g. "accept_agb_required").
# The frontend maps them to translated texts.


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    role = serializers.ChoiceField(choices=Role.choices)
    accept_agb = serializers.BooleanField()
    accept_datenschutz = serializers.BooleanField()

    def validate_email(self, value):
        return value.strip().lower()

    def validate_password(self, value):
        request = self.context.get("request")
        lang = translation.get_language_from_request(request) if request else translation.get_language()

        with translation.override(lang or "en"):
            try:
                run_password_validators(value)
            except DjangoValidationError as exc:
                messages = []
                for err in getattr(exc, "error_list", [exc]):
                    code = getattr(err, "code", None)
                    params = getattr(err, "params", {}) or {}
                    min_len = params.get("min_length", 8)

                    if code == "password_too_short":
                        # Стандартний ngettext
                        msg = ngettext(
                            "This password is too short. It must contain at least %(min_length)d character.",
                            "This password is too short. It must contain at least %(min_length)d characters.",
                            min_len,
                        ) % {"min_length": min_len}

                        # Якщо в системі локаль de не скомпільована, підставляємо німецький текст
                        current_lang = translation.get_language()
                        if current_lang and current_lang.startswith("de") and "Passwort" not in msg:
                            msg = f"Dieses Passwort ist zu kurz. Es muss mindestens {min_len} Zeichen enthalten."
                        elif current_lang and current_lang.startswith("uk"):
                            msg = f"Цей пароль занадто короткий. Він має містити щонайменше {min_len} символів."

                        messages.append(serializers.ErrorDetail(msg, code="password_too_short"))
                    else:
                        for m in getattr(err, "messages", [str(err)]):
                            messages.append(serializers.ErrorDetail(m, code=code or "invalid"))

                raise serializers.ValidationError(messages)

        return value

    def validate_accept_agb(self, value):
        if value is not True:
            raise serializers.ValidationError("accept_agb_required")
        return value

    def validate_accept_datenschutz(self, value):
        if value is not True:
            raise serializers.ValidationError("accept_datenschutz_required")
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)

    def validate_email(self, value):
        return value.strip().lower()


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(trim_whitespace=False, max_length=128)


class MeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    role = serializers.CharField()
    email_verified = serializers.BooleanField(source="is_email_verified")
