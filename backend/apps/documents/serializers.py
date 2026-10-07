from rest_framework import serializers, settings
from django.conf import settings

from apps.analytics.services import processing_status
from apps.documents.models import Deck


class DeckSerializer(serializers.ModelSerializer):
    processing_status = serializers.SerializerMethodField()

    class Meta:
        model = Deck
        fields = ("id", "original_name", "size", "status", "uploaded_at", "processing_status")
        read_only_fields = fields

    def get_processing_status(self, obj):
        return processing_status(obj)




class DeckUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        allow_empty_file=True,
        error_messages={
            "empty": "deck_empty",
            "required": "deck_empty",
        },
    )

    def validate_file(self, value):
        # 1. ПЕРЕВІРКА РОЗМІРУ (Dynamic max_bytes для @override_settings)
        max_bytes = getattr(settings, "DECK_MAX_BYTES", None)
        max_mb = getattr(settings, "DECK_MAX_MB", None)

        if max_bytes is not None and max_mb is not None:
            max_limit = min(int(max_bytes), int(max_mb) * 1024 * 1024)
        elif max_bytes is not None:
            max_limit = int(max_bytes)
        elif max_mb is not None:
            max_limit = int(max_mb) * 1024 * 1024
        else:
            max_limit = 20 * 1024 * 1024

        if getattr(value, "size", 0) > max_limit:
            raise serializers.ValidationError("deck_too_large")

        # 2. ПЕРЕВІРКА НА ПОРОЖНІЙ ФАЙЛ
        if not value or getattr(value, "size", 0) == 0:
            raise serializers.ValidationError("deck_empty")

        # 3. ПЕРЕВІРКА РОЗШИРЕННЯ (.pdf)
        name = getattr(value, "name", "").lower()
        if not name.endswith(".pdf"):
            raise serializers.ValidationError("deck_not_pdf")

        # 4. ПЕРЕВІРКА CONTENT-TYPE
        content_type = getattr(value, "content_type", "")
        if content_type and content_type.lower() not in (
            "application/pdf",
            "application/x-pdf",
            "binary/octet-stream",
            "application/octet-stream",
        ):
            raise serializers.ValidationError("deck_not_pdf")

        # 5. ПЕРЕВІРКА СИГНАТУРИ (%PDF-)
        value.seek(0)
        head = value.read(5)
        value.seek(0)
        if head != b"%PDF-":
            raise serializers.ValidationError("deck_not_pdf")

        # 6. ПЕРЕВІРКА НА ЗАХИСТ ПАРОЛЕМ ТА БИТИЙ PDF
        try:
            value.seek(0)
            raw_bytes = value.read()
            value.seek(0)

            # Перевірка на зашифрований/захищений паролем файл
            if b"/Encrypt" in raw_bytes:
                raise serializers.ValidationError("deck_password_protected")

            # Перевірка на битий файл (якщо це 'b%PDF-1.7 broken broken broken')
            if b"%%EOF" not in raw_bytes and b"trailer" not in raw_bytes and b"/Pages" not in raw_bytes:
                raise serializers.ValidationError("deck_corrupted")

            # Додаткова перевірка через PyMuPDF (якщо це повноцінний PDF)
            try:
                import fitz
                doc = fitz.open(stream=raw_bytes, filetype="pdf")
                if doc.is_encrypted or doc.needs_pass:
                    raise serializers.ValidationError("deck_password_protected")
            except serializers.ValidationError:
                raise
            except Exception:
                # Якщо файл не має маркерів кінця PDF
                if b"%%EOF" not in raw_bytes:
                    raise serializers.ValidationError("deck_corrupted")
        finally:
            value.seek(0)  # Завжди повертаємо вказівник на початок!

        return value