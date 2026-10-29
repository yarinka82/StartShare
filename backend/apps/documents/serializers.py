from rest_framework import serializers
from django.conf import settings
from typing import TypedDict
from apps.accounts.models import PlatformConfig
from apps.analytics.services import processing_status
from apps.documents.models import PitchDeck
from common.validators import get_max_deck_size_bytes






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




    