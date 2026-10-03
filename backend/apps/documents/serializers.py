from rest_framework import serializers

from .models import PitchDeck


class PitchDeckSerializer(serializers.ModelSerializer):
    processing_status = serializers.SerializerMethodField()

    class Meta:
        model = PitchDeck
        fields = ["id", "file", "uploaded_at", "processing_status"]
        read_only_fields = ["id", "uploaded_at", "processing_status"]

    def get_processing_status(self, obj):
        # Отримуємо статус задачі (DRAFT_READY, QUEUED, PROCESSING, FAILED)
        job = getattr(obj, "job", None)
        if job is None:
            job = getattr(obj, "teaserjob", None) or TeaserJob.objects.filter(deck=obj).first()
        return job.state if job else None

    def validate_file(self, value):
        # 1. Перевірка розширення
        if not value.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("Дозволено завантажувати лише PDF-файли.")

        # 2. Перевірка Magic Bytes
        value.seek(0)
        header = value.read(5)
        value.seek(0)
        if header != b"%PDF-":
            raise serializers.ValidationError("Файл пошкоджений або не є коректним PDF.")

        return value