from rest_framework import serializers
from django.conf import settings
from typing import TypedDict
from apps.accounts.models import PlatformConfig
from apps.analytics.services import processing_status
from apps.documents.models import PitchDeck
from common.validators import get_max_deck_size_bytes


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



class DeckSerializer(serializers.ModelSerializer):
    # Сохраняем алиасы для полной обратной совместимости с фронтендом и тестами:
    size = serializers.IntegerField(source="file_size_bytes", read_only=True)
    status = serializers.CharField(source="processing_state", read_only=True)
    processing_status = serializers.SerializerMethodField()

    class Meta:
        model = PitchDeck
        fields = (
            "id",
            "original_name",
            "size",
            "file_size_bytes",
            "status",
            "processing_state",
            "uploaded_at",
            "processing_status",
            "keep_original",
        )
        read_only_fields = fields

    def get_processing_status(self, obj) -> str:
        return processing_status(obj) or obj.processing_state


class DeckUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        allow_empty_file=True,
        error_messages={
            "empty": "deck_empty",
            "required": "deck_empty",
        },
    )
    
    def validate_file(self, value):
        # 1. Размер: единый источник истины (PlatformConfig -> дефолт из settings)
        if value.size > get_max_deck_size_bytes():
            raise serializers.ValidationError("deck_too_large")

        # 2. ПРОВЕРКА НА ПУСТОЙ ФАЙЛ
        if not value or getattr(value, "size", 0) == 0:
            raise serializers.ValidationError("deck_empty")

        # 3. ПРОВЕРКА РАСШИРЕНИЯ (.pdf)
        name = getattr(value, "name", "").lower()
        if not name.endswith(".pdf"):
            raise serializers.ValidationError("deck_not_pdf")

        # 4. ПРОВЕРКА CONTENT-TYPE
        content_type = getattr(value, "content_type", "")
        if content_type and content_type.lower() not in (
            "application/pdf",
            "application/x-pdf",
            "binary/octet-stream",
            "application/octet-stream",
        ):
            raise serializers.ValidationError("deck_not_pdf")

        # 5. ПРОВЕРКА СИГНАТУРЫ (%PDF-)
        value.seek(0)
        head = value.read(5)
        value.seek(0)
        if head != b"%PDF-":
            raise serializers.ValidationError("deck_not_pdf")

        # 6. ПРОВЕРКА НА ПАРОЛЬ И ПОВРЕЖДЁННЫЙ PDF
        try:
            value.seek(0)
            raw_bytes = value.read()
            value.seek(0)

            # Проверка на зашифрованный/защищённый паролем файл
            if b"/Encrypt" in raw_bytes:
                raise serializers.ValidationError("deck_password_protected")

            # Проверка на битый файл
            if b"%%EOF" not in raw_bytes and b"trailer" not in raw_bytes and b"/Pages" not in raw_bytes:
                raise serializers.ValidationError("deck_corrupted")

            # Дополнительная валидация через PyMuPDF
            try:
                import pymupdf
                doc = pymupdf.open(stream=raw_bytes, filetype="pdf")
                if doc.is_encrypted or doc.needs_pass:
                    raise serializers.ValidationError("deck_password_protected")
            except serializers.ValidationError:
                raise
            except Exception:
                if b"%%EOF" not in raw_bytes:
                    raise serializers.ValidationError("deck_corrupted")
        finally:
            value.seek(0)  # Всегда возвращаем указатель в начало!

        return value



class PlatformConfigSerializer(serializers.ModelSerializer):
    ai_providers = serializers.SerializerMethodField()
    # Для azure_openai модель пустая: если у модельного поля нет blank=True, добавьте его.
    ai_model = serializers.CharField(allow_blank=True, required=False)
    
    class Meta:
        model = PlatformConfig
        fields = [
            "ai_provider", "ai_model", "ai_temperature",
            "max_deck_size_mb", "deck_retention_hours", "draft_expiry_days",
            "min_digest_cards", "max_digest_cards", "intro_request_expiry_days",
            "updated_at", "ai_providers",
        ]
        read_only_fields = ["updated_at"]
        extra_kwargs = {
            "ai_temperature": {"min_value": 0, "max_value": 1},
            "max_deck_size_mb": {"min_value": 1, "max_value": 200},
            "deck_retention_hours": {"min_value": 1},
            "draft_expiry_days": {"min_value": 1},
            "min_digest_cards": {"min_value": 1},
            "max_digest_cards": {"min_value": 1},
            "intro_request_expiry_days": {"min_value": 1},
        }
    
    def get_ai_providers(self, obj):
        return AI_PROVIDER_CATALOG
    
    def validate(self, attrs):
        inst = self.instance
        
        if "ai_provider" in attrs or "ai_model" in attrs:
            provider_id = attrs.get("ai_provider", inst.ai_provider)
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
            
            if provider["models"]:
                model = attrs.get("ai_model", inst.ai_model)
                if isinstance(model, list):
                    model = model[0] if model else None
                if model not in {m["id"] for m in provider["models"]}:
                    raise serializers.ValidationError(
                        {"ai_model": "Ця модель недоступна для обраного провайдера."}
                    )
            else:
                attrs["ai_model"] = ""
        
        lo = attrs.get("min_digest_cards", inst.min_digest_cards)
        hi = attrs.get("max_digest_cards", inst.max_digest_cards)
        if lo > hi:
            raise serializers.ValidationError(
                {"min_digest_cards": "Мінімум не може бути більшим за максимум."}
            )
        return attrs
    
    