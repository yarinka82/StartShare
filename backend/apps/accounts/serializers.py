from typing import TypedDict

from django.conf import settings
from django.contrib.auth.password_validation import validate_password as run_password_validators
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import translation
from django.utils.translation import ngettext
from rest_framework import serializers

from apps.accounts.models import UserRole, PlatformConfig


# NOTE: custom validation messages are stable error codes (e.g. "accept_agb_required").
# The frontend maps them to translated texts.


class RegisterSerializer(serializers.Serializer):
    # Дозволені для публічної реєстрації ролі (виключаємо staff)
    PUBLIC_ROLES = [
        (UserRole.STARTUP, "Startup"),
        (UserRole.INVESTOR, "Investor"),
    ]
    
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    
    # 2. Використовуємо UserRole
    role = serializers.ChoiceField(choices=PUBLIC_ROLES)
    
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


class AIModel(TypedDict):
    id: str
    label: str


class AIProvider(TypedDict):
    id: str
    label: str
    models: list[AIModel]


AI_PROVIDER_CATALOG: list[AIProvider] = [
    {
        "id": "gemini",
        "label": "Google Gemini",
        "models": [
            {"id": "gemini-3.8-flash", "label": "Gemini 3.8 Flash (Fast / Recommended)"},
            {"id": "gemini-3.7-flash", "label": "Gemini 3.7 Flash"},
        ],
    },
    {
        "id": "openai",
        "label": "OpenAI",
        "models": [{"id": "gpt-4o-mini", "label": "GPT-4o-mini"}],
    },
    {
        "id": "azure_openai",
        "label": "Azure OpenAI",
        "models": [],  # модель = AZURE_OPENAI_DEPLOYMENT
    },
]

_CATALOG_BY_ID: dict[str, AIProvider] = {p["id"]: p for p in AI_PROVIDER_CATALOG}


def _provider_configured(provider_id: str) -> bool:
    if provider_id == "gemini":
        return bool(getattr(settings, "TEASER_GEMINI_API_KEY", ""))
    if provider_id == "openai":
        return bool(getattr(settings, "OPENAI_API_KEY", ""))
    if provider_id == "azure_openai":
        return all(
            getattr(settings, name, "")
            for name in ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT")
        )
    return False



class PlatformConfigSerializer(serializers.ModelSerializer):
    ai_providers = serializers.SerializerMethodField()
    ai_model = serializers.CharField(allow_blank=True, required=False)

    class Meta:
        model = PlatformConfig
        fields = [
            "ai_provider",
            "ai_model",
            "ai_temperature",
            "max_deck_size_mb",
            "deck_retention_hours",
            "draft_expiry_days",
            "min_digest_cards",
            "max_digest_cards",
            "intro_request_expiry_days",
            "intro_reminder_days",
            "card_active_days",
            "surveys_enabled",
            "survey_day_first",
            "survey_day_second",
            "updated_at",
            "ai_providers",
        ]
        read_only_fields = ["updated_at"]
        extra_kwargs = {
            "ai_temperature": {"min_value": 0, "max_value": 1},
            "max_deck_size_mb": {"min_value": 1, "max_value": 200},
            "deck_retention_hours": {"min_value": 1},
            "draft_expiry_days": {"min_value": 1},
            "min_digest_cards": {"min_value": 1},
            "max_digest_cards": {"min_value": 1},
            "intro_request_expiry_days": {"min_value": 1, "max_value": 60},
            "intro_reminder_days": {"min_value": 1, "max_value": 30},
            "card_active_days": {"min_value": 1, "max_value": 30},
            "survey_day_first": {"min_value": 1},
            "survey_day_second": {"min_value": 1},
        }

    def get_ai_providers(self, obj):
        return AI_PROVIDER_CATALOG

    def validate(self, attrs):
        inst = self.instance

        # 1. Ваша існуюча перевірка AI провайдерів та AVV (REQ-39)
        if "ai_provider" in attrs or "ai_model" in attrs:
            provider_id = attrs.get("ai_provider", getattr(inst, "ai_provider", None))
            if isinstance(provider_id, list):
                provider_id = provider_id[0] if provider_id else None

            provider = _CATALOG_BY_ID.get(provider_id)
            if provider is None:
                raise serializers.ValidationError(
                    {"ai_provider": f"Невідомий провайдер: {provider_id!r}."}
                )
            if not getattr(settings, "TEASER_AVV_SIGNED", False):
                raise serializers.ValidationError(
                    {"ai_provider": "Віддалений провайдер потребує підписаного AVV (REQ-39)."}
                )
            if not _provider_configured(provider_id):
                raise serializers.ValidationError(
                    {"ai_provider": "Для цього провайдера не задано ключі/налаштування на сервері."}
                )

            if provider.get("models"):
                model = attrs.get("ai_model", getattr(inst, "ai_model", ""))
                if isinstance(model, list):
                    model = model[0] if model else None
                if model not in {m["id"] for m in provider["models"]}:
                    raise serializers.ValidationError(
                        {"ai_model": "Ця модель недоступна для обраного провайдера."}
                    )
            else:
                attrs["ai_model"] = ""

        # 2. Ваша перевірка лімітів дайджесту
        lo = attrs.get("min_digest_cards", getattr(inst, "min_digest_cards", 3))
        hi = attrs.get("max_digest_cards", getattr(inst, "max_digest_cards", 5))
        if lo > hi:
            raise serializers.ValidationError(
                {"min_digest_cards": "Мінімум карток не може бути більшим за максимум."}
            )

        # 3. Логічна перевірка: нагадування стартапу має бути раніше за таймаут закриття запиту
        reminder = attrs.get("intro_reminder_days", getattr(inst, "intro_reminder_days", 4))
        expiry = attrs.get("intro_request_expiry_days", getattr(inst, "intro_request_expiry_days", 7))
        if reminder >= expiry:
            raise serializers.ValidationError(
                {"intro_reminder_days": f"Дні нагадування ({reminder}) повинні бути меншими за термін закриття запиту ({expiry})."}
            )

        # 4. Перевірка порядку опитувань
        s1 = attrs.get("survey_day_first", getattr(inst, "survey_day_first", 14))
        s2 = attrs.get("survey_day_second", getattr(inst, "survey_day_second", 30))
        if s1 >= s2:
            raise serializers.ValidationError(
                {"survey_day_first": "Перше опитування має відбутися раніше за друге."}
            )

        return attrs
